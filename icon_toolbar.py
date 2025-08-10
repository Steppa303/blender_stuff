# blender_version: (4, 0, 0)
bl_info = {
    "name": "Icon Toolbar",
    "author": "AI Assistant (GPT-4) & Community Feedback",
    "version": (2, 0, 0),
    "blender": (4, 0, 0),
    "location": "3D View > Sidebar (N Panel) > Icon Bar",
    "description": "Creates a persistent, custom icon toolbar. Right-click any UI element to add it instantly.",
    "warning": "",
    "doc_url": "",
    "category": "Interface",
}

import bpy
from bpy.props import StringProperty, EnumProperty, CollectionProperty, IntProperty
from bpy.types import Operator, PropertyGroup, UIList, Panel, AddonPreferences

# --- Data Structure for a single Toolbar Item ---
class ICONBAR_PG_item(PropertyGroup):
    """Stores the data for a single button. Uses simple properties for robust registration."""
    name: StringProperty(name="Name", description="Display name for the item")
    rna_path: StringProperty(name="RNA Path", description="The RNA path for the operator")
    data_path: StringProperty(name="Data Path", description="The path to the data block for properties")
    prop_name: StringProperty(name="Property Name", description="The name of the property")
    is_operator: bpy.props.BoolProperty(name="Is Operator", default=True)
    icon: StringProperty(name="Icon", default='QUESTION')

# --- UI List for the Addon Preferences ---
class ICONBAR_UL_items(UIList):
    """Defines the layout for the list in the addon preferences, allowing name edits."""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            # --- UPDATED --- Makes the name an editable field.
            row.label(text="", icon=item.icon)
            row.prop(item, "name", text="", emboss=False)

# --- Addon Preferences ---
class ICONBAR_preferences(AddonPreferences):
    bl_idname = __name__
    items: CollectionProperty(type=ICONBAR_PG_item)
    active_index: IntProperty(default=0)

    def draw(self, context):
        layout = self.layout; layout.label(text="Manage your custom icon buttons here.")
        row = layout.row(); col = row.column()
        col.template_list("ICONBAR_UL_items", "", self, "items", self, "active_index", rows=5)
        col = row.column(align=True); col.operator("iconbar.list_remove", icon='REMOVE', text="")
        col.separator(); col.operator("iconbar.list_move", icon='TRIA_UP', text="").direction = 'UP'
        col.operator("iconbar.list_move", icon='TRIA_DOWN', text="").direction = 'DOWN'

# --- Operators for Managing the List in Preferences ---
class ICONBAR_OT_list_remove(Operator):
    bl_idname = "iconbar.list_remove"; bl_label = "Remove Item"
    def execute(self, context):
        prefs = context.preferences.addons[__name__].preferences
        if prefs.items:
            prefs.items.remove(prefs.active_index)
            if prefs.active_index > 0: prefs.active_index -= 1
        return {'FINISHED'}

class ICONBAR_OT_list_move(Operator):
    bl_idname = "iconbar.list_move"; bl_label = "Move Item"
    direction: EnumProperty(items=(('UP', 'Up', ''), ('DOWN', 'Down', '')))
    def execute(self, context):
        prefs = context.preferences.addons[__name__].preferences; idx = prefs.active_index
        if self.direction == 'UP':
            if idx > 0: prefs.items.move(idx, idx - 1); prefs.active_index -= 1
        else:
            if idx < len(prefs.items) - 1: prefs.items.move(idx, idx + 1); prefs.active_index += 1
        return {'FINISHED'}

# --- The Main Operator to Add an Item from the UI ---
class ICONBAR_OT_add_from_context(Operator):
    bl_idname = "iconbar.add_from_context"; bl_label = "Add to Icon Bar"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        op = getattr(context, "button_operator", None)
        prop = getattr(context, "button_prop", None)
        ptr = getattr(context, "button_pointer", None)
        return op or (prop and ptr)

    # --- UPDATED --- No more dialog! All logic is in execute() for instant adding.
    def execute(self, context):
        op = getattr(context, "button_operator", None)
        prop = getattr(context, "button_prop", None)
        prefs = context.preferences.addons[__name__].preferences
        new_item = prefs.items.add()
        
        report_name = ""

        if op:
            new_item.is_operator = True
            new_item.rna_path = f"bpy.ops.{op.bl_idname}()"
            new_item.name = op.bl_label if op.bl_label else op.bl_idname.replace("_", " ").title()
            new_item.icon = 'PLUGIN' # Default icon for operators
            report_name = new_item.name
        elif prop:
            ptr = context.button_pointer
            new_item.is_operator = False
            new_item.data_path = ptr.path_from_id()
            new_item.prop_name = prop.property
            new_item.name = prop.name
            report_name = new_item.name
            icon_id = getattr(prop, 'icon', 0)
            if icon_id != 0:
                try:
                    new_item.icon = bpy.app.icons.from_int(icon_id).name
                except:
                    new_item.icon = 'DOT' # Fallback
            else:
                new_item.icon = 'DOT'
        else:
            # Should not happen due to poll(), but as a fallback, remove the empty item
            prefs.items.remove(len(prefs.items)-1)
            self.report({'WARNING'}, "Could not identify UI element.")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Added '{report_name}' to Icon Bar.")
        # Trigger a redraw of the panel
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        return {'FINISHED'}

# --- The Toolbar Panel in the 3D View Sidebar ---
class VIEW3D_PT_icon_toolbar(Panel):
    bl_label = "Icon Bar"; bl_space_type = 'VIEW_3D'; bl_region_type = 'UI'; bl_category = "Icon Bar"
    def draw(self, context):
        layout = self.layout; prefs = context.preferences.addons[__name__].preferences
        if not prefs.items:
            col = layout.column(align=True); col.label(text="Toolbar is empty.")
            col.label(text="Right-click any button or"); col.label(text="property and choose:")
            col.label(text="'Add to Icon Bar'", icon='ADD')
            return
        flow = layout.grid_flow(row_major=True, columns=4, even_columns=True, even_rows=True, align=True)
        for item in prefs.items:
            if item.is_operator:
                flow.operator(item.rna_path, text="", icon=item.icon)
            else:
                try:
                    resolved_obj = context.path_resolve(item.data_path)
                    if resolved_obj: flow.prop(resolved_obj, item.prop_name, text="", icon=item.icon)
                    else: flow.label(text="", icon=item.icon).active = False
                except (ReferenceError, TypeError, AttributeError): flow.label(text="", icon=item.icon).active = False

def menu_func(self, context):
    self.layout.separator(); self.layout.operator(ICONBAR_OT_add_from_context.bl_idname)

classes = (
    ICONBAR_PG_item, ICONBAR_UL_items, ICONBAR_preferences,
    ICONBAR_OT_list_remove, ICONBAR_OT_list_move,
    ICONBAR_OT_add_from_context, VIEW3D_PT_icon_toolbar,
)

def register():
    for cls in classes: bpy.utils.register_class(cls)
    bpy.types.UI_MT_button_context_menu.append(menu_func)

def unregister():
    bpy.types.UI_MT_button_context_menu.remove(menu_func)
    for cls in reversed(classes): bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
