#
# Counterfactual intervention demo for SPEAR (apartment_0000).
#
# Pipeline: launch sim -> spawn RGB+depth camera -> pick a target object ->
#   capture BEFORE -> intervention 1: move+rotate the object -> capture ->
#   intervention 2: remove a nearby object -> capture ->
#   intervention 3: add a new object (StarterContent chair) -> capture ->
# save per-condition RGB / colorized depth / raw depth .npy, RGB difference
# heatmaps vs BEFORE, and a contact sheet.
#
# Built from the idioms in examples/render_image_dataset and examples/debug_draw.
#

import json
import math
import os

import cv2
import numpy as np
import spear

DEMO_DIR = os.path.realpath(os.path.dirname(__file__))
OUT_DIR = os.path.join(DEMO_DIR, "output")

MOVE_TARGET_PATTERNS = ["Chair"]
REMOVE_TARGET_PATTERNS = ["Vase", "Cushion", "Lamp", "Plant", "Prop", "Picture"]
EXCLUDE_PATTERNS = ["Wall", "Floor", "Ceiling", "Casement", "Carpet", "Door", "Curtain", "Mirror"]

CONDITIONS = []  # (name, callable) filled in main


def rotator_look_at(src, dst):
    dx, dy, dz = dst["X"] - src["X"], dst["Y"] - src["Y"], dst["Z"] - src["Z"]
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
    return {"Pitch": pitch, "Yaw": yaw, "Roll": 0.0}


def colorize_depth(depth_m, max_m=7.5):
    d = depth_m - np.min(depth_m)
    d = np.clip(d / min(max(np.max(d), 1e-6), max_m), 0.0, 1.0)
    return cv2.applyColorMap((d * 255.0).astype(np.uint8), cv2.COLORMAP_VIRIDIS)


def capture(instance, components, name):
    instance.step(num_frames=3)  # let TAA/Lumen settle after any scene change
    with instance.begin_frame():
        pass
    with instance.end_frame():
        rgb = components["rgb"].read_pixels()["arrays"]["data"]
        depth = components["depth"].read_pixels()["arrays"]["data"]
    rgb_bgr = rgb[:, :, [0, 1, 2]].copy()
    depth_m = depth[:, :, 0].astype(np.float32)
    cv2.imwrite(os.path.join(OUT_DIR, f"{name}_rgb.png"), rgb_bgr)
    cv2.imwrite(os.path.join(OUT_DIR, f"{name}_depth.png"), colorize_depth(depth_m))
    np.save(os.path.join(OUT_DIR, f"{name}_depth_meters.npy"), depth_m)
    spear.log(f"Captured condition '{name}'")
    return rgb_bgr, depth_m


if __name__ == "__main__":

    os.makedirs(OUT_DIR, exist_ok=True)

    config = spear.get_config(user_config_files=[os.path.join(DEMO_DIR, "user_config.yaml")])
    spear.configure_system(config=config)
    instance = spear.Instance(config=config)
    game = instance.get_game()

    # --- discover the scene's actors ------------------------------------------------
    with instance.begin_frame():
        actors = game.unreal_service.find_actors_as_dict()
        names = sorted(actors.keys())
        with open(os.path.join(OUT_DIR, "actor_inventory.json"), "w") as f:
            json.dump(names, f, indent=2)
        spear.log(f"Scene contains {len(names)} actors (inventory saved).")

        def matches(name, patterns):
            return any(p.lower() in name.lower() for p in patterns)

        move_candidates = [n for n in names if matches(n, MOVE_TARGET_PATTERNS) and not matches(n, EXCLUDE_PATTERNS)]
        assert move_candidates, "no move target found - inspect actor_inventory.json"
        move_name = move_candidates[0]
        move_actor = actors[move_name]
        raw = move_actor.K2_GetActorLocation()  # returned FVector dicts use lowercase keys
        move_loc = {"X": raw["x"], "Y": raw["y"], "Z": raw["z"]}
        spear.log(f"Move target: {move_name} at {move_loc}")

        # remove-target: nearest decor actor to the move target (stays in frame)
        remove_name, remove_actor, best_d = None, None, 1e12
        for n in names:
            if n == move_name or not matches(n, REMOVE_TARGET_PATTERNS) or matches(n, EXCLUDE_PATTERNS):
                continue
            loc = actors[n].K2_GetActorLocation()
            d = math.dist((loc["x"], loc["y"], loc["z"]), (move_loc["X"], move_loc["Y"], move_loc["Z"]))
            if d < best_d:
                remove_name, remove_actor, best_d = n, actors[n], d
        spear.log(f"Remove target: {remove_name} ({best_d:.0f} cm from move target)")

        # --- camera: 3 m back from the move target, eye height, looking at it -------
        cam_loc = {"X": move_loc["X"] - 260.0, "Y": move_loc["Y"] - 140.0, "Z": move_loc["Z"] + 150.0}
        cam_rot = rotator_look_at(cam_loc, {"X": move_loc["X"], "Y": move_loc["Y"], "Z": move_loc["Z"] + 40.0})

        bp_camera_sensor_uclass = game.unreal_service.load_class(uclass="AActor", name="/SpContent/Blueprints/BP_CameraSensor.BP_CameraSensor_C")
        bp_camera_sensor = game.unreal_service.spawn_actor(uclass=bp_camera_sensor_uclass, location=cam_loc, rotation=cam_rot)
        components = {}
        for key, long_name in [("rgb", "DefaultSceneRoot.final_tone_curve_hdr_"), ("depth", "DefaultSceneRoot.sp_depth_meters_")]:
            c = game.unreal_service.get_component_by_name(uclass="USceneComponent", actor=bp_camera_sensor, component_name=long_name)
            c.Initialize()
            c.initialize_sp_funcs()
            components[key] = c

    with instance.end_frame():
        pass

    # --- condition 0: BEFORE --------------------------------------------------------
    rgb_before, _ = capture(instance, components, "0_before")

    # --- condition 1: MOVE + ROTATE the chair ---------------------------------------
    with instance.begin_frame():
        mesh_component = game.unreal_service.get_component_by_class(actor=move_actor, uclass="UStaticMeshComponent")
        mesh_component.SetMobility(NewMobility="Movable")
        rot = move_actor.K2_GetActorRotation()  # lowercase keys, same as K2_GetActorLocation
        move_actor.K2_SetActorLocationAndRotation(
            NewLocation={"X": move_loc["X"] + 60.0, "Y": move_loc["Y"] + 40.0, "Z": move_loc["Z"]},
            NewRotation={"Pitch": rot["pitch"], "Yaw": rot["yaw"] + 45.0, "Roll": rot["roll"]})
    with instance.end_frame():
        pass
    rgb_move, _ = capture(instance, components, "1_move_rotate")

    # --- condition 2: REMOVE a nearby object ----------------------------------------
    with instance.begin_frame():
        if remove_actor is not None:
            game.unreal_service.destroy_actor(actor=remove_actor)
    with instance.end_frame():
        pass
    rgb_remove, _ = capture(instance, components, "2_remove")

    # --- condition 3: ADD a new object (StarterContent chair) -----------------------
    with instance.begin_frame():
        new_mesh = game.unreal_service.load_object(uclass="UStaticMesh", name="/Game/StarterContent/Props/SM_Chair.SM_Chair")
        new_actor = game.unreal_service.spawn_actor(
            uclass="AStaticMeshActor",
            location={"X": move_loc["X"] - 40.0, "Y": move_loc["Y"] - 120.0, "Z": move_loc["Z"]},
            rotation={"Pitch": 0.0, "Yaw": cam_rot["Yaw"] + 180.0, "Roll": 0.0},  # face the camera
            spawn_parameters={"SpawnCollisionHandlingOverride": "AlwaysSpawn"})
        new_mesh_component = game.unreal_service.get_component_by_class(actor=new_actor, uclass="UStaticMeshComponent")
        new_mesh_component.SetMobility(NewMobility="Movable")
        new_mesh_component.SetStaticMesh(NewMesh=new_mesh)
    with instance.end_frame():
        pass
    rgb_add, _ = capture(instance, components, "3_add")

    # --- difference heatmaps vs BEFORE + contact sheet ------------------------------
    rgbs = {"0_before": rgb_before, "1_move_rotate": rgb_move, "2_remove": rgb_remove, "3_add": rgb_add}
    tiles = []
    for name, rgb in rgbs.items():
        diff = cv2.applyColorMap(cv2.cvtColor(cv2.absdiff(rgb, rgb_before), cv2.COLOR_BGR2GRAY), cv2.COLORMAP_INFERNO)
        cv2.imwrite(os.path.join(OUT_DIR, f"{name}_diff_vs_before.png"), diff)
        labeled = rgb.copy()
        cv2.putText(labeled, name, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        tiles.append(np.vstack([labeled, diff]))
    cv2.imwrite(os.path.join(OUT_DIR, "contact_sheet.png"), np.hstack(tiles))

    # --- cleanup ---------------------------------------------------------------------
    with instance.begin_frame():
        pass
    with instance.end_frame():
        for c in components.values():
            c.terminate_sp_funcs()
            c.Terminate()
        game.unreal_service.destroy_actor(actor=bp_camera_sensor)

    instance.close()
    spear.log("Done. Outputs in: ", OUT_DIR)
