"""Generate the VPN Doctor logo with VectorCraft (ArtCraft suite).

Usage:
    python3 assets/logo/generate_logo.py default > logo-default.json
    vectorcraft-cli run --commands logo-default.json --export vpn-doctor.svg --export vpn-doctor.png

Variants: "default" (teal to blue gradient) and "wasteland" (green phosphor
wireframe with an outer glow). The shield protects, the cross diagnoses and
the pulse is the health of the connection.
"""
import json
import sys

SHIELD = "M256 84 L396 134 L396 258 C396 350 334 412 256 444 C178 412 116 350 116 258 L116 134 Z"
PULSE = "M150 300 L206 300 L226 262 L254 348 L284 236 L304 300 L362 300"
CROSS = ("M240 136 L272 136 L272 172 L308 172 L308 204 L272 204 L272 240 "
         "L240 240 L240 204 L204 204 L204 172 L240 172 Z")


def steps(variant):
    s = [{"command": "file.new", "params": {"name": "VPN Doctor", "width": 512, "height": 512, "units": "Pixels"}}]

    def add(command, params):
        s.append({"command": command, "params": params})
        return f"${len(s) - 1}.id"

    if variant == "default":
        bg = add("shape.rectangle", {"x": 24, "y": 24, "width": 464, "height": 464, "radius": 112})
        add("paint.setFill", {"id": bg, "gradient": {"kind": "linear", "angle": -45, "stops": [
            {"offset": 0, "color": "#14b8a6"}, {"offset": 1, "color": "#1d4ed8"}]}})
        add("paint.setStroke", {"id": bg, "none": True})
        shield = add("path.create", {"d": SHIELD})
        add("paint.setFill", {"id": shield, "color": "#ffffff"})
        add("paint.setStroke", {"id": shield, "none": True})
        cross = add("path.create", {"d": CROSS})
        add("paint.setFill", {"id": cross, "color": "#0f766e"})
        add("paint.setStroke", {"id": cross, "none": True})
        pulse = add("path.create", {"d": PULSE})
        add("paint.setFill", {"id": pulse, "none": True})
        add("paint.setStroke", {"id": pulse, "color": "#1d4ed8"})
        add("stroke.set", {"id": pulse, "weight": 18, "cap": "round", "join": "round"})
    else:  # wasteland: green phosphor wireframe
        green, screen = "#45ee8a", "#05160d"
        bg = add("shape.rectangle", {"x": 24, "y": 24, "width": 464, "height": 464, "radius": 64})
        add("paint.setFill", {"id": bg, "color": screen})
        add("paint.setStroke", {"id": bg, "color": green})
        add("stroke.set", {"id": bg, "weight": 6})
        shield = add("path.create", {"d": SHIELD})
        add("paint.setFill", {"id": shield, "color": "#071910"})
        add("paint.setStroke", {"id": shield, "color": green})
        add("stroke.set", {"id": shield, "weight": 14, "join": "round"})
        cross = add("path.create", {"d": CROSS})
        add("paint.setFill", {"id": cross, "color": green})
        add("paint.setStroke", {"id": cross, "none": True})
        pulse = add("path.create", {"d": PULSE})
        add("paint.setFill", {"id": pulse, "none": True})
        add("paint.setStroke", {"id": pulse, "color": green})
        add("stroke.set", {"id": pulse, "weight": 16, "cap": "round", "join": "round"})
        for target in (shield, cross, pulse):
            add("effect.apply", {"effect": "stylize.outerGlow", "ids": [target],
                                 "params": {"color": green, "blur": 14, "opacity": 70, "mode": "screen"}})
    return s


json.dump(steps(sys.argv[1]), sys.stdout, ensure_ascii=False, indent=1)
