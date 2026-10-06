#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gi
gi.require_version('Gimp', '3.0')
gi.require_version('GimpUi', '3.0')
from gi.repository import Gimp, GimpUi, GObject, GLib, Gegl

class LandscapeRampPlugin (Gimp.PlugIn):

    def do_query_procedures(self):
        return ["python-fu-landscape-ramp-v3"]

    def do_create_procedure(self, name):
        procedure = Gimp.ImageProcedure.new(
            self, name,
            Gimp.PDBProcType.PLUGIN,
            self.run, None
        )
        procedure.set_documentation(
            "Rysuj rampę na landscape (GIMP 3)",
            "Rysuje prostokątną rampę na podstawie aktywnej ścieżki i kolorów na jej końcach.",
            name
        )
        procedure.set_menu_label("Rampa na landscape...")
        procedure.add_menu_path("<Image>/Filters/Render")
        procedure.set_attribution("Twoje Imię", "Twoje Imię", "2026")

        # Argumenty wejściowe (GIMP 3 style)
        procedure.add_argument_from_property(self, "ramp-width")
        return procedure

    def run(self, procedure, run_mode, image, drawables, config, data):
        if len(drawables) == 0:
            return procedure.new_return_values(Gimp.PDBStatusType.CALL_ERROR, GLib.Error())

        drawable = drawables[0]
        ramp_width = config.get_property("ramp-width")

        # Sprawdzenie ścieżki
        vectors = image.get_active_vectors()
        if not vectors:
            print("Błąd: Brak aktywnej ścieżki.")
            return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, None)

        strokes = vectors.get_strokes()
        if not strokes:
            return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, None)

        points = strokes[0].get_points()[1] # W GIMP 3 zwraca strukturę z punktami
        if len(points) < 6:
            return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, None)

        x1, y1 = points[2], points[3]
        x2, y2 = points[-4], points[-3]

        dx, dy = x2 - x1, y2 - y1
        length = (dx**2 + dy**2)**0.5
        if length == 0:
            return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, None)

        image.undo_group_start()

        # Pobieranie pikseli z użyciem GEGL w GIMP 3
        color_start = drawable.get_pixel(int(x1), int(y1))
        color_end = drawable.get_pixel(int(x2), int(y2))

        Gimp.context_set_foreground(color_start)
        Gimp.context_set_background(color_end)

        nx, ny = -dy / length, dx / length
        half_w = ramp_width / 2.0

        selection_points = [
            x1 + nx * half_w, y1 + ny * half_w,
            x1 - nx * half_w, y1 - ny * half_w,
            x2 - nx * half_w, y2 - ny * half_w,
            x2 + nx * half_w, y2 + ny * half_w
        ]

        pdb = Gimp.get_pdb()
        # Zaznaczenie polygonu przez PDB w GIMP 3
        pdb.run_procedure('gimp-image-select-polygon', [
            GObject.Value(Gimp.Image, image),
            GObject.Value(Gimp.ChannelOps, Gimp.ChannelOps.REPLACE),
            GObject.Value(GObject.TYPE_INT, len(selection_points)),
            GObject.Value(Gimp.FloatArray, selection_points)
        ])

        # Wypełnienie gradientem
        pdb.run_procedure('gimp-drawable-edit-gradient-fill', [
            GObject.Value(Gimp.Drawable, drawable),
            GObject.Value(Gimp.GradientType, Gimp.GradientType.LINEAR),
            GObject.Value(GObject.TYPE_DOUBLE, 0.0),
            GObject.Value(GObject.TYPE_BOOLEAN, False),
            GObject.Value(GObject.TYPE_DOUBLE, 0.0),
            GObject.Value(GObject.TYPE_DOUBLE, 0.0),
            GObject.Value(GObject.TYPE_BOOLEAN, False),
            GObject.Value(GObject.TYPE_DOUBLE, x1),
            GObject.Value(GObject.TYPE_DOUBLE, y1),
            GObject.Value(GObject.TYPE_DOUBLE, x2),
            GObject.Value(GObject.TYPE_DOUBLE, y2)
        ])

        pdb.run_procedure('gimp-selection-none', [GObject.Value(Gimp.Image, image)])

        image.undo_group_end()
        Gimp.displays_flush()

        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, None)

# Rejestracja właściwości (Szerokość rampy)
GObject.type_register(LandscapeRampPlugin)
Gimp.main(LandscapeRampPlugin.__gtype__, None)