#
# Paired counterfactual VIDEO generator for SPEAR (apartment_0000).
#
# Extends counterfactual_demo/run.py from single-frame captures to frame-aligned
# VIDEO PAIRS. It renders the SAME scripted camera orbit twice:
#   - "factual"        : the scene as-is
#   - "counterfactual" : the scene after ONE intervention (move / remove / add)
# Because SPEAR's frame loop is deterministic (fixed 1/30 s delta time) and the
# camera trajectory is scripted rather than physics-driven, the two rollouts stay
# frame-aligned -- only the intervention differs. Outputs per-rollout RGB and depth
# mp4s plus a labeled side-by-side  factual | counterfactual | diff  comparison mp4.
#
# Encodes with the ffmpeg bundled in imageio-ffmpeg:  pip install -e "python[examples]"
#
# Usage:
#   conda activate spear-env
#   python counterfactual_video.py --intervention move --num-frames 36
#

import argparse
import math
import os

import cv2
import imageio_ffmpeg
import numpy as np
import spear

DEMO_DIR = os.path.realpath(os.path.dirname(__file__))
OUT_DIR = os.path.join(DEMO_DIR, "output_video")

MOVE_TARGET_PATTERNS = ["Chair"]
REMOVE_TARGET_PATTERNS = ["Vase", "Cushion", "Lamp", "Plant", "Prop", "Picture"]
EXCLUDE_PATTERNS = ["Wall", "Floor", "Ceiling", "Casement", "Carpet", "Door", "Curtain", "Mirror"]


def matches(name, patterns):
    return any(p.lower() in name.lower() for p in patterns)


def rotator_look_at(src, dst):
    dx, dy, dz = dst["X"] - src["X"], dst["Y"] - src["Y"], dst["Z"] - src["Z"]
    return {"Pitch": math.degrees(math.atan2(dz, math.hypot(dx, dy))),
            "Yaw": math.degrees(math.atan2(dy, dx)), "Roll": 0.0}


def orbit_pose(center, i, n, radius=295.0, height=150.0, arc_deg=55.0):
    # sweep a horizontal arc "behind" the target (base heading -X), always looking at it
    t = i / max(n - 1, 1)
    ang = math.radians(180.0 - arc_deg / 2.0 + arc_deg * t)
    loc = {"X": center["X"] + radius * math.cos(ang),
           "Y": center["Y"] + radius * math.sin(ang),
           "Z": center["Z"] + height}
    return loc, rotator_look_at(loc, {"X": center["X"], "Y": center["Y"], "Z": center["Z"] + 40.0})


def colorize_depth(depth_m, max_m=7.5):
    d = depth_m - np.min(depth_m)
    d = np.clip(d / min(max(np.max(d), 1e-6), max_m), 0.0, 1.0)
    return cv2.applyColorMap((d * 255.0).astype(np.uint8), cv2.COLORMAP_VIRIDIS)


def label(img, text):
    out = img.copy()
    cv2.rectangle(out, (0, 0), (12 * len(text) + 20, 34), (0, 0, 0), -1)
    cv2.putText(out, text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    return out


def capture_orbit(instance, components, camera, center, num_frames, settle):
    # render the scripted orbit; return (BGR frames, colorized-depth frames)
    rgb_frames, depth_frames = [], []
    for i in range(num_frames):
        loc, rot = orbit_pose(center, i, num_frames)
        with instance.begin_frame():
            camera.K2_SetActorLocationAndRotation(NewLocation=loc, NewRotation=rot)
        with instance.end_frame():
            pass
        instance.step(num_frames=settle)  # let TAA/Lumen settle at the new view
        with instance.begin_frame():
            pass
        with instance.end_frame():
            rgb = components["rgb"].read_pixels()["arrays"]["data"]
            depth = components["depth"].read_pixels()["arrays"]["data"]
        rgb_frames.append(rgb[:, :, [0, 1, 2]].copy())  # channel order matches run.py (BGR for cv2)
        depth_frames.append(colorize_depth(depth[:, :, 0].astype(np.float32)))
    return rgb_frames, depth_frames


def write_mp4(path, bgr_frames, fps):
    # encode via the ffmpeg bundled in imageio-ffmpeg (no system ffmpeg needed), as in render_image_multi_view
    h, w = bgr_frames[0].shape[:2]
    writer = imageio_ffmpeg.write_frames(path, size=(w, h), fps=fps, quality=8, macro_block_size=16)
    writer.send(None)  # seed the generator
    for f in bgr_frames:
        writer.send(np.ascontiguousarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)).tobytes())  # ffmpeg wants RGB bytes
    writer.close()
    spear.log("Wrote ", path)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--intervention", choices=["move", "remove", "add"], default="move")
    parser.add_argument("--num-frames", type=int, default=36)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--settle", type=int, default=3)
    parser.add_argument("--rpc-timeout", type=float, default=60.0,
                        help="RPC client timeout (s); raised above the 2 s default so on-demand PSO/shader "
                             "compilation hitches while orbiting to new views don't abort the run")
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)

    config = spear.get_config(user_config_files=[os.path.join(DEMO_DIR, "user_config.yaml")])
    config.defrost()
    config.SPEAR.INSTANCE.CLIENT_INTERNAL_TIMEOUT_SECONDS = args.rpc_timeout  # absorb PSO-compile hitches on long orbits
    config.freeze()
    spear.configure_system(config=config)
    instance = spear.Instance(config=config)
    game = instance.get_game()

    # --- discover scene + choose intervention target(s) ------------------------------
    with instance.begin_frame():
        actors = game.unreal_service.find_actors_as_dict()
        names = sorted(actors.keys())

        move_candidates = [n for n in names if matches(n, MOVE_TARGET_PATTERNS) and not matches(n, EXCLUDE_PATTERNS)]
        assert move_candidates, "no chair-like target found in scene"
        target_name = move_candidates[0]
        target_actor = actors[target_name]
        raw = target_actor.K2_GetActorLocation()  # getters return lowercase keys
        center = {"X": raw["x"], "Y": raw["y"], "Z": raw["z"]}
        spear.log(f"Orbit center = {target_name} at {center}")

        # nearest decor object (used by the 'remove' intervention)
        remove_name, remove_actor, best = None, None, 1e12
        for n in names:
            if n == target_name or not matches(n, REMOVE_TARGET_PATTERNS) or matches(n, EXCLUDE_PATTERNS):
                continue
            loc = actors[n].K2_GetActorLocation()
            d = math.dist((loc["x"], loc["y"], loc["z"]), (center["X"], center["Y"], center["Z"]))
            if d < best:
                remove_name, remove_actor, best = n, actors[n], d

        # --- spawn the camera sensor, aimed at the target ---------------------------
        loc0, rot0 = orbit_pose(center, 0, args.num_frames)
        cam_uclass = game.unreal_service.load_class(uclass="AActor", name="/SpContent/Blueprints/BP_CameraSensor.BP_CameraSensor_C")
        camera = game.unreal_service.spawn_actor(uclass=cam_uclass, location=loc0, rotation=rot0)
        components = {}
        for key, comp in [("rgb", "DefaultSceneRoot.final_tone_curve_hdr_"), ("depth", "DefaultSceneRoot.sp_depth_meters_")]:
            c = game.unreal_service.get_component_by_name(uclass="USceneComponent", actor=camera, component_name=comp)
            c.Initialize()
            c.initialize_sp_funcs()
            components[key] = c
        # spawned BP actors are usually Movable, but make it explicit so we can reposition each frame
        try:
            root = game.unreal_service.get_component_by_name(uclass="USceneComponent", actor=camera, component_name="DefaultSceneRoot")
            root.SetMobility(NewMobility="Movable")
        except Exception as e:
            spear.log("camera SetMobility skipped: ", e)
    with instance.end_frame():
        pass

    # --- factual rollout -------------------------------------------------------------
    spear.log("Rendering factual rollout (", args.num_frames, " frames)...")
    fac_rgb, fac_depth = capture_orbit(instance, components, camera, center, args.num_frames, args.settle)

    # --- apply the intervention ------------------------------------------------------
    spear.log("Applying intervention: ", args.intervention)
    with instance.begin_frame():
        if args.intervention == "move":
            mesh = game.unreal_service.get_component_by_class(actor=target_actor, uclass="UStaticMeshComponent")
            mesh.SetMobility(NewMobility="Movable")  # scene furniture is Static; must enable movement first
            rot = target_actor.K2_GetActorRotation()
            target_actor.K2_SetActorLocationAndRotation(
                NewLocation={"X": center["X"] + 60.0, "Y": center["Y"] + 40.0, "Z": center["Z"]},
                NewRotation={"Pitch": rot["pitch"], "Yaw": rot["yaw"] + 45.0, "Roll": rot["roll"]})
        elif args.intervention == "remove":
            assert remove_actor is not None, "no decor object found to remove"
            spear.log("  removing ", remove_name)
            game.unreal_service.destroy_actor(actor=remove_actor)
        elif args.intervention == "add":
            new_mesh = game.unreal_service.load_object(uclass="UStaticMesh", name="/Game/StarterContent/Props/SM_Chair.SM_Chair")
            new_actor = game.unreal_service.spawn_actor(
                uclass="AStaticMeshActor",
                location={"X": center["X"] - 40.0, "Y": center["Y"] - 120.0, "Z": center["Z"]},
                rotation={"Pitch": 0.0, "Yaw": rot0["Yaw"] + 180.0, "Roll": 0.0},
                spawn_parameters={"SpawnCollisionHandlingOverride": "AlwaysSpawn"})
            nmc = game.unreal_service.get_component_by_class(actor=new_actor, uclass="UStaticMeshComponent")
            nmc.SetMobility(NewMobility="Movable")
            nmc.SetStaticMesh(NewMesh=new_mesh)
    with instance.end_frame():
        pass

    # --- counterfactual rollout (identical orbit) ------------------------------------
    spear.log("Rendering counterfactual rollout...")
    cf_rgb, cf_depth = capture_orbit(instance, components, camera, center, args.num_frames, args.settle)

    # --- encode videos ---------------------------------------------------------------
    tag = args.intervention
    write_mp4(os.path.join(OUT_DIR, "factual_rgb.mp4"), fac_rgb, args.fps)
    write_mp4(os.path.join(OUT_DIR, f"counterfactual_{tag}_rgb.mp4"), cf_rgb, args.fps)
    write_mp4(os.path.join(OUT_DIR, "factual_depth.mp4"), fac_depth, args.fps)
    write_mp4(os.path.join(OUT_DIR, f"counterfactual_{tag}_depth.mp4"), cf_depth, args.fps)

    comp = []
    for fa, cf in zip(fac_rgb, cf_rgb):
        diff = cv2.applyColorMap(cv2.cvtColor(cv2.absdiff(fa, cf), cv2.COLOR_BGR2GRAY), cv2.COLORMAP_INFERNO)
        comp.append(np.hstack([label(fa, "factual"), label(cf, f"counterfactual ({tag})"), label(diff, "diff")]))
    write_mp4(os.path.join(OUT_DIR, f"comparison_{tag}.mp4"), comp, args.fps)

    # --- cleanup ---------------------------------------------------------------------
    with instance.begin_frame():
        pass
    with instance.end_frame():
        for c in components.values():
            c.terminate_sp_funcs()
            c.Terminate()
        game.unreal_service.destroy_actor(actor=camera)
    instance.close()
    spear.log("Done. Videos in: ", OUT_DIR)
