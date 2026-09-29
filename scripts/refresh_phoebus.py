"""Apply a restrained visual refresh to the existing Phoebus display.

All widgets, PVs, rules, actions, macros, and trace settings are inherited from
gui-legacy.bob.  This script changes only static presentation properties.
"""

from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / "bobs"


def set_color(parent, tag, rgb):
    node = parent.find(tag)
    if node is None:
        node = ET.SubElement(parent, tag)
    color = node.find("color")
    if color is None:
        color = ET.SubElement(node, "color")
    color.attrib.clear()
    color.set("red", str(rgb[0]))
    color.set("green", str(rgb[1]))
    color.set("blue", str(rgb[2]))


tree = ET.parse(ROOT / "gui-legacy.bob")
display = tree.getroot()
display.find("name").text = "Timing Simulation · Operator View"
display.find("width").text = "1290"
set_color(display, "background_color", (232, 240, 244))

navy = (13, 42, 57)
ink = (25, 53, 67)
muted = (80, 108, 120)
teal = (13, 126, 143)
paper = (250, 253, 254)

for widget in display.iter("widget"):
    kind = widget.get("type")
    label = widget.findtext("text", "")
    if widget in display and int(widget.findtext("x", "0")) >= 1015:
        widget.find("width").text = "260"
        for child in widget.findall("widget"):
            child_kind = child.get("type")
            if child_kind == "textupdate" and child.findtext("x", "0") == "138":
                child.find("width").text = "116"
            elif child_kind in ("label", "spinner", "tank", "checkbox") and child.findtext("x", "0") in ("0", "2"):
                width = child.find("width")
                if width is not None and int(width.text) >= 186:
                    width.text = str(int(width.text) + 70)
            elif child_kind == "group" and child.findtext("width", "0") == "190":
                child.find("width").text = "260"
    if kind == "group":
        # Only top-level panels receive a card background; nested groups keep
        # their original transparency, geometry, and macro inheritance.
        if widget in display and widget.findtext("y", "0") != "0":
            set_color(widget, "background_color", paper)
            transparent = widget.find("transparent")
            if transparent is not None:
                transparent.text = "false"
    elif kind == "label":
        if label == "$(TITLE)":
            set_color(widget, "foreground_color", (255, 255, 255))
            set_color(widget, "background_color", navy)
        elif widget.find("background_color") is not None and widget.find("transparent") is not None and widget.find("transparent").text == "false":
            set_color(widget, "background_color", navy if len(label) < 28 and "$(" not in label else (220, 237, 241))
            set_color(widget, "foreground_color", (255, 255, 255) if len(label) < 28 and "$(" not in label else ink)
        elif "$(" not in label:
            set_color(widget, "foreground_color", ink)
    elif kind == "textupdate":
        # Readbacks receive the same high-contrast treatment while alarm rules
        # retain their original dynamic colors.
        set_color(widget, "foreground_color", teal)
    elif kind == "action_button":
        if "Dump" in label or widget.findtext("pv_name", "") == "SIM:BEAM:DUMP":
            set_color(widget, "background_color", (181, 49, 58))
            set_color(widget, "foreground_color", (255, 255, 255))
        elif "Reset" in label or "RESET" in label:
            set_color(widget, "background_color", (35, 94, 124))
            set_color(widget, "foreground_color", (255, 255, 255))

# Improve the display's title bar without changing its contained widgets.
header = next(w for w in display.findall("widget") if w.get("type") == "group" and w.findtext("y", "0") == "0")
header.find("width").text = "1290"
header.find("widget/width").text = "1290"
set_color(header, "background_color", navy)
header.find("transparent").text = "false"

ET.indent(tree, space="  ")
tree.write(ROOT / "gui.bob", encoding="UTF-8", xml_declaration=True)
