print("APP STARTING...")
import os
import sqlite3
import webbrowser
import urllib.parse
import csv
import subprocess
import shutil
import tempfile
from datetime import datetime
import importlib

PROFILE_FILE = "profile_name.txt"

def _try_load_kivy():
    try:
        app_mod = importlib.import_module("kivy.app")
        clock_mod = importlib.import_module("kivy.clock")
        core_window_mod = importlib.import_module("kivy.core.window")
        box_mod = importlib.import_module("kivy.uix.boxlayout")
        button_mod = importlib.import_module("kivy.uix.button")
        grid_mod = importlib.import_module("kivy.uix.gridlayout")
        label_mod = importlib.import_module("kivy.uix.label")
        popup_mod = importlib.import_module("kivy.uix.popup")
        scroll_mod = importlib.import_module("kivy.uix.scrollview")
        spinner_mod = importlib.import_module("kivy.uix.spinner")
        text_mod = importlib.import_module("kivy.uix.textinput")
        animation_mod = importlib.import_module("kivy.animation")
        return {
            "App": getattr(app_mod, "App"),
            "Clock": getattr(clock_mod, "Clock"),
            "Window": getattr(core_window_mod, "Window"),
            "BoxLayout": getattr(box_mod, "BoxLayout"),
            "Button": getattr(button_mod, "Button"),
            "GridLayout": getattr(grid_mod, "GridLayout"),
            "Label": getattr(label_mod, "Label"),
            "Popup": getattr(popup_mod, "Popup"),
            "ScrollView": getattr(scroll_mod, "ScrollView"),
            "Spinner": getattr(spinner_mod, "Spinner"),
            "TextInput": getattr(text_mod, "TextInput"),
            "Animation": getattr(animation_mod, "Animation"),
        }
    except Exception:
        return None


kivy_objects = _try_load_kivy()
if kivy_objects:
    App = kivy_objects["App"]
    Clock = kivy_objects["Clock"]
    Window = kivy_objects["Window"]
    BoxLayout = kivy_objects["BoxLayout"]
    Button = kivy_objects["Button"]
    GridLayout = kivy_objects["GridLayout"]
    Label = kivy_objects["Label"]
    Popup = kivy_objects["Popup"]
    ScrollView = kivy_objects["ScrollView"]
    Spinner = kivy_objects["Spinner"]
    TextInput = kivy_objects["TextInput"]
else:
    # Kivy not available — lightweight shims for static analysis and minimal runtime
    class Clock:
        @staticmethod
        def schedule_once(func, dt):
            try:
                func(None)
            except Exception:
                pass


    class Window:
        clearcolor = (1, 1, 1, 1)


    class _WidgetShim:
        def __init__(self, *args, **kwargs):
            self.children = []
            self.text = kwargs.get("text", "")
            self.size = kwargs.get("size", (0, 0))
            self.size_hint_y = kwargs.get("size_hint_y", None)

        def add_widget(self, w):
            self.children.append(w)

        def bind(self, **kwargs):
            return None

        def setter(self, name):
            def _set(v):
                setattr(self, name, v)

            return _set


    class App(_WidgetShim):
        def run(self):
            return None


    class BoxLayout(_WidgetShim):
        pass


    class Button(_WidgetShim):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)


    class GridLayout(_WidgetShim):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)


    class Label(_WidgetShim):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)


    class Popup(_WidgetShim):
        def open(self):
            return None

        def dismiss(self):
            return None


    class ScrollView(_WidgetShim):
        pass


    class Spinner(_WidgetShim):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)


    class TextInput(_WidgetShim):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)

Window.clearcolor = (0.97, 0.97, 0.98, 1)

STATUSES = ["Paid", "Unpaid", "Pending"]
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


def format_money(value):
    return f"{value:,.2f}" if isinstance(value, (int, float)) else value


class MasjidReceiptManagerApp(App):
    def build(self):
        self.db = sqlite3.connect("members.db", check_same_thread=False)
        self.cursor = self.db.cursor()
        self.create_tables()

        self.selected_month = datetime.now().strftime("%B")
        self.selected_year = str(datetime.now().year)
        self.selected_status = "All"
        self.editing_member_id = None
        self.profile_name = self.load_profile_name()
        self.dark_mode = False
        self.update_theme_colors()

        root = BoxLayout(orientation="vertical", padding=10, spacing=10)

        title_bar = BoxLayout(size_hint_y=None, height=44, spacing=10)
        profile_button = Button(text="Profile", size_hint=(0.18, 1), background_color=self.button_color, color=self.text_color, on_release=self.open_profile_popup)
        self.profile_label = Label(text=self.profile_name, halign="left", valign="middle", font_size='20sp', color=self.text_color)
        self.profile_label.bind(size=self.profile_label.setter("text_size"))
        developer_label = Label(text="Developed by AFFAN18", halign="right", valign="middle", font_size='12sp', color=self.secondary_text_color)
        developer_label.bind(size=developer_label.setter("text_size"))
        title_bar.add_widget(profile_button)
        title_bar.add_widget(self.profile_label)
        title_bar.add_widget(developer_label)
        root.add_widget(title_bar)

        header = BoxLayout(size_hint_y=None, height=44, spacing=10)
        self.month_spinner = Spinner(text=self.selected_month, values=MONTHS, size_hint=(0.28, 1))
        self.year_spinner = Spinner(text=self.selected_year, values=self.get_year_values(), size_hint=(0.22, 1))
        self.status_spinner = Spinner(text=self.selected_status, values=["All"] + STATUSES, size_hint=(0.25, 1))
        self.search_input = TextInput(text="", hint_text="Search member", multiline=False, size_hint=(0.15, 1), height=40)
        search_button = Button(text="Search", size_hint=(0.10, 1), background_color=self.button_color, color=self.text_color, on_release=lambda *_: self.search_member())
        self.month_spinner.bind(text=self.on_filter_change)
        self.year_spinner.bind(text=self.on_filter_change)
        self.status_spinner.bind(text=self.on_filter_change)
        self.search_input.bind(text=lambda instance, value: self.search_member())

        header.add_widget(self.month_spinner)
        header.add_widget(self.year_spinner)
        header.add_widget(self.status_spinner)
        header.add_widget(self.search_input)
        header.add_widget(search_button)
        root.add_widget(header)

        action_bar = BoxLayout(size_hint_y=None, height=44, spacing=10)
        add_button = Button(text="Add Member", background_color=self.button_color, color=self.text_color, on_release=self.open_add_popup)
        import_csv_button = Button(text="Import CSV", background_color=self.button_color, color=self.text_color, on_release=lambda *_: self.import_members_csv())
        export_csv_button = Button(text="Export CSV", background_color=self.button_color, color=self.text_color, on_release=lambda *_: self.export_members_csv())
        preview_button = Button(text="Print Preview", background_color=self.button_color, color=self.text_color, on_release=lambda *_: self.open_print_preview())
        print_button = Button(text="Print", background_color=self.button_color, color=self.text_color, on_release=lambda *_: self.print_members())
        refresh_button = Button(text="Refresh", background_color=self.button_color, color=self.text_color, on_release=lambda *_: self.refresh_members())
        theme_button = Button(text="Dark Mode", background_color=self.button_color, color=self.text_color, on_release=self.toggle_theme)
        action_bar.add_widget(add_button)
        action_bar.add_widget(import_csv_button)
        action_bar.add_widget(export_csv_button)
        action_bar.add_widget(preview_button)
        action_bar.add_widget(print_button)
        action_bar.add_widget(refresh_button)
        action_bar.add_widget(theme_button)
        root.add_widget(action_bar)

        totals = BoxLayout(size_hint_y=None, height=30, spacing=10)
        self.month_total_label = Label(text="Month Total: 0", halign="left", valign="middle", color=self.text_color, font_size='16sp')
        self.year_total_label = Label(text="Year Total: 0", halign="right", valign="middle", color=self.text_color, font_size='16sp')
        self.month_total_label.bind(size=self.month_total_label.setter("text_size"))
        self.year_total_label.bind(size=self.year_total_label.setter("text_size"))
        totals.add_widget(self.month_total_label)
        totals.add_widget(self.year_total_label)
        root.add_widget(totals)

        self.member_list_area = ScrollView()
        self.member_list_layout = GridLayout(cols=1, spacing=10, size_hint_y=None, padding=(0, 0))
        self.member_list_layout.bind(minimum_height=self.member_list_layout.setter("height"))
        self.member_list_area.add_widget(self.member_list_layout)
        root.add_widget(self.member_list_area)

        Clock.schedule_once(lambda *_: self.refresh_members(), 0)
        Clock.schedule_once(lambda *_: self.show_startup_splash(), 0.2)
        return root

    def get_year_values(self):
        current = datetime.now().year
        return [str(y) for y in range(current - 2, current + 3)]

    def create_tables(self):
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL,
                month TEXT NOT NULL,
                year TEXT NOT NULL,
                hold INTEGER NOT NULL DEFAULT 0,
                months_pending INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        self.db.commit()
        try:
            self.cursor.execute("ALTER TABLE members ADD COLUMN months_pending INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        self.db.commit()

    def on_filter_change(self, spinner, text):
        self.selected_month = self.month_spinner.text
        self.selected_year = self.year_spinner.text
        self.selected_status = self.status_spinner.text
        self.refresh_members()

    def on_member_status_change(self, spinner, text):
        self.month_input.values = MONTHS + ["Common"]
        if self.month_input.text not in self.month_input.values:
            self.month_input.text = self.selected_month
        if text == "Pending":
            self.pending_months_input.disabled = False
            self.pending_months_input.opacity = 1
        else:
            self.pending_months_input.disabled = True
            self.pending_months_input.opacity = 0.5

    def update_theme_colors(self):
        if self.dark_mode:
            self.bg_color = (0.09, 0.11, 0.14, 1)
            self.panel_color = (0.14, 0.17, 0.22, 1)
            self.text_color = (1, 1, 1, 1)
            self.secondary_text_color = (0.75, 0.82, 0.95, 1)
            self.button_color = (0.18, 0.22, 0.30, 1)
            self.input_bg = (0.12, 0.14, 0.18, 1)
        else:
            self.bg_color = (0.97, 0.97, 0.98, 1)
            self.panel_color = (1, 1, 1, 1)
            self.text_color = (0.08, 0.08, 0.08, 1)
            self.secondary_text_color = (0.35, 0.38, 0.43, 1)
            self.button_color = (0.92, 0.93, 0.96, 1)
            self.input_bg = (1, 1, 1, 1)
        try:
            Window.clearcolor = self.bg_color
        except Exception:
            pass

    def toggle_theme(self, *_):
        self.dark_mode = not self.dark_mode
        self.update_theme_colors()
        self.refresh_members()
        if hasattr(self, "menu_popup") and self.menu_popup:
            self.menu_popup.dismiss()
        if hasattr(self, "menu_popup") and self.menu_popup:
            self.menu_popup.dismiss()

    def refresh_members(self):
        self.member_list_layout.clear_widgets()
        members = self.query_members(self.selected_year, self.selected_month, self.selected_status)
        if not members:
            self.member_list_layout.add_widget(Label(text="No records found for this month.", size_hint_y=None, height=40, color=self.text_color))
        for member in members:
            self.member_list_layout.add_widget(self.build_member_row(member))
        month_total, year_total = self.calculate_totals(self.selected_year, self.selected_month)
        self.month_total_label.text = f"Month Total: {format_money(month_total)}"
        self.year_total_label.text = f"Year Total: {format_money(year_total)}"

    def query_members(self, year, month, status_filter="All"):
        if month == "Common":
            if status_filter == "All":
                self.cursor.execute(
                    "SELECT id, name, phone, amount, status, hold, month, year, months_pending FROM members WHERE year=? AND month=? ORDER BY name",
                    (year, "Common"),
                )
            else:
                self.cursor.execute(
                    "SELECT id, name, phone, amount, status, hold, month, year, months_pending FROM members WHERE year=? AND month=? AND status=? ORDER BY name",
                    (year, "Common", status_filter),
                )
            rows = self.cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "phone": row[2],
                    "amount": row[3],
                    "status": row[4],
                    "hold": bool(row[5]),
                    "month": row[6],
                    "year": row[7],
                    "months_pending": row[8],
                    "source": "common",
                }
                for row in rows
            ]

        params = (year, month) if status_filter == "All" else (year, month, status_filter)
        status_clause = "" if status_filter == "All" else " AND status=?"
        self.cursor.execute(
            f"SELECT id, name, phone, amount, status, hold, month, year, months_pending FROM members WHERE year=? AND month=?{status_clause} ORDER BY name",
            params,
        )
        month_rows = self.cursor.fetchall()

        members = []
        month_keys = set()
        for row in month_rows:
            members.append(
                {
                    "id": row[0],
                    "name": row[1],
                    "phone": row[2],
                    "amount": row[3],
                    "status": row[4],
                    "hold": bool(row[5]),
                    "month": row[6],
                    "year": row[7],
                    "months_pending": row[8],
                    "source": "month",
                }
            )
            month_keys.add((row[1], row[2]))

        # Always add common members to other months, regardless of status filter
        self.cursor.execute(
            "SELECT id, name, phone, amount, status, hold, month, year, months_pending FROM members WHERE year=? AND month=? ORDER BY name",
            (year, "Common"),
        )
        common_rows = self.cursor.fetchall()
        for row in common_rows:
            key = (row[1], row[2])
            if key in month_keys:
                continue
            members.append(
                {
                    "id": row[0],
                    "name": row[1],
                    "phone": row[2],
                    "amount": row[3],
                    "status": "Unpaid",
                    "hold": bool(row[5]),
                    "month": month,
                    "year": year,
                    "months_pending": row[8],
                    "source": "common_template",
                    "common_id": row[0],
                }
            )

        members.sort(key=lambda m: m["name"])
        return members

    def search_member(self):
        search_text = self.search_input.text.strip().lower()
        members = self.query_members(self.selected_year, self.selected_month, self.selected_status)
        if not search_text:
            self.refresh_members()
            return

        filtered = [m for m in members if search_text in m["name"].lower()]
        self.member_list_layout.clear_widgets()
        if not filtered:
            self.member_list_layout.add_widget(Label(text="No matching member found for this month.", size_hint_y=None, height=40, color=self.text_color))
            return

        for member in filtered:
            self.member_list_layout.add_widget(self.build_member_row(member))

    def calculate_totals(self, year, month):
        self.cursor.execute(
            "SELECT SUM(amount) FROM members WHERE year=? AND (month=? OR month=?) AND status=?",
            (year, month, "Common", "Paid"),
        )
        month_total = self.cursor.fetchone()[0] or 0.0
        self.cursor.execute(
            "SELECT SUM(amount) FROM members WHERE year=? AND status=?",
            (year, "Paid"),
        )
        year_total = self.cursor.fetchone()[0] or 0.0
        return month_total, year_total

    def build_member_row(self, member):
        row = BoxLayout(orientation="vertical", size_hint_y=None, height=240, padding=10, spacing=8)

        if member["hold"]:
            name_color = (1, 0.2, 0.2, 1)
            status_color = (1, 0.2, 0.2, 1)
        elif member["status"] == "Paid":
            name_color = (0.0, 0.6, 0.0, 1)
            status_color = (0.0, 0.6, 0.0, 1)
        elif member["status"] == "Unpaid":
            name_color = (1.0, 0.55, 0.0, 1)
            status_color = (1.0, 0.55, 0.0, 1)
        else:
            name_color = self.text_color
            status_color = self.secondary_text_color

        row.add_widget(Label(text=f"[b]{member['name']}[/b]", markup=True, size_hint_y=None, height=36, font_size='18sp', color=name_color))
        row.add_widget(Label(text=f"{member['phone']}", size_hint_y=None, height=24, font_size='14sp', color=self.secondary_text_color))
        pending_suffix = ""
        if member["status"] == "Pending" and member["months_pending"]:
            total = member["amount"] * member["months_pending"]
            pending_suffix = f" ({member['months_pending']} months = {format_money(total)})"
        row.add_widget(Label(text=f"Amount: {format_money(member['amount'])}{pending_suffix}", size_hint_y=None, height=26, color=self.secondary_text_color))
        row.add_widget(Label(text=f"Status: {member['status']}   |   Hold: {'Yes' if member['hold'] else 'No'}", size_hint_y=None, height=26, color=status_color))

        buttons = GridLayout(cols=2, spacing=8, size_hint_y=None, height=60)
        buttons.add_widget(Button(text="Cycle Status", background_color=self.button_color, color=self.text_color, on_release=lambda inst, m=member: self.cycle_status(m)))
        buttons.add_widget(Button(text="Hold/Resume", background_color=self.button_color, color=self.text_color, on_release=lambda inst, m=member: self.toggle_hold(m)))
        buttons.add_widget(Button(text="WhatsApp", background_color=self.button_color, color=self.text_color, on_release=lambda inst, m=member: self.send_whatsapp_message(m)))
        buttons.add_widget(Button(text="Edit", background_color=self.button_color, color=self.text_color, on_release=lambda inst, m=member: self.open_edit_popup(m)))
        row.add_widget(buttons)

        remove_row = BoxLayout(size_hint_y=None, height=32)
        remove_row.add_widget(Button(text="Remove", background_color=self.button_color, color=self.text_color, on_release=lambda inst, m=member: self.delete_member(m)))
        row.add_widget(remove_row)
        return row

    def cycle_status(self, member):
        if not member:
            return
        current_index = STATUSES.index(member["status"]) if member["status"] in STATUSES else 0
        new_status = STATUSES[(current_index + 1) % len(STATUSES)]
        if member.get("source") == "common_template":
            self.cursor.execute(
                "INSERT INTO members (name, phone, amount, status, month, year, hold, months_pending) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    member["name"],
                    member["phone"],
                    member["amount"],
                    new_status,
                    self.selected_month,
                    self.selected_year,
                    int(member["hold"]),
                    member.get("months_pending", 0),
                ),
            )
            self.db.commit()
        else:
            self.update_member_field(member["id"], "status", new_status)

    def toggle_hold(self, member):
        if not member:
            return
        new_hold = 0 if member["hold"] else 1
        if member.get("source") == "common_template":
            self.cursor.execute(
                "INSERT INTO members (name, phone, amount, status, month, year, hold, months_pending) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    member["name"],
                    member["phone"],
                    member["amount"],
                    member["status"],
                    self.selected_month,
                    self.selected_year,
                    new_hold,
                    member.get("months_pending", 0),
                ),
            )
            self.db.commit()
        else:
            self.update_member_field(member["id"], "hold", new_hold)

    def get_member(self, member_id):
        self.cursor.execute(
            "SELECT id, name, phone, amount, status, hold, month, year FROM members WHERE id=?",
            (member_id,),
        )
        row = self.cursor.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "name": row[1],
            "phone": row[2],
            "amount": row[3],
            "status": row[4],
            "hold": bool(row[5]),
            "month": row[6],
            "year": row[7],
        }

    def update_member_field(self, member_id, field, value):
        self.cursor.execute(f"UPDATE members SET {field}=? WHERE id=?", (value, member_id))
        self.db.commit()
        self.refresh_members()

    def delete_member(self, member):
        if isinstance(member, int):
            self.show_message("Unable to remove member. Please refresh and try again.")
            return
        if member.get("source") == "common_template":
            self.show_message("Cannot remove a common template from this month. Edit or override it instead.")
            return
        self.cursor.execute("DELETE FROM members WHERE id=?", (member["id"],))
        self.db.commit()
        self.refresh_members()

    def open_add_popup(self, *_):
        self.editing_member_id = None
        self.show_member_form()

    def open_edit_popup(self, member):
        self.editing_member_id = member["id"]
        self.show_member_form(member)

    def show_member_form(self, member=None):
        title = "Edit Member" if member else "Add Member"
        content = BoxLayout(orientation="vertical", spacing=10, padding=10)

        self.name_input = TextInput(text=member["name"] if member else "", hint_text="Name", multiline=False, size_hint_y=None, height=40)
        phone_value = "+91 "
        if member:
            phone_value = member["phone"] or "+91 "
            if not phone_value.strip().startswith("+91"):
                phone_value = "+91 " + phone_value.strip()
        self.phone_input = TextInput(text=phone_value, hint_text="Phone number", multiline=False, size_hint_y=None, height=40)
        self.amount_input = TextInput(text=str(member["amount"]) if member else "", hint_text="Amount", multiline=False, input_filter="float", size_hint_y=None, height=40)
        self.status_input = Spinner(text=member["status"] if member else STATUSES[1], values=STATUSES, size_hint_y=None, height=40)
        self.pending_months_input = TextInput(text=str(member["months_pending"]) if member else "0", hint_text="Pending months", multiline=False, input_filter="int", size_hint_y=None, height=40)
        self.month_input = Spinner(text=member["month"] if member else self.selected_month, values=MONTHS + ["Common"], size_hint_y=None, height=40)
        self.year_input = Spinner(text=member["year"] if member else self.selected_year, values=self.get_year_values(), size_hint_y=None, height=40)
        self.status_input.bind(text=self.on_member_status_change)
        self.on_member_status_change(self.status_input, self.status_input.text)
        if self.status_input.text != "Pending":
            self.pending_months_input.disabled = True
            self.pending_months_input.opacity = 0.5

        if member:
            self.original_member_month = member["month"]
            self.original_member_year = member["year"]
            self.original_member_status = member["status"]
            self.original_member_source = member.get("source", "month")
        else:
            self.original_member_month = None
            self.original_member_year = None
            self.original_member_status = None
            self.original_member_source = None

        content.add_widget(Label(text="Name", size_hint_y=None, height=24))
        content.add_widget(self.name_input)
        content.add_widget(Label(text="Phone number", size_hint_y=None, height=24))
        content.add_widget(self.phone_input)
        content.add_widget(Label(text="Amount", size_hint_y=None, height=24))
        content.add_widget(self.amount_input)
        content.add_widget(Label(text="Status", size_hint_y=None, height=24))
        content.add_widget(self.status_input)
        content.add_widget(Label(text="Pending months", size_hint_y=None, height=24))
        content.add_widget(self.pending_months_input)
        content.add_widget(Label(text="Month", size_hint_y=None, height=24))
        content.add_widget(self.month_input)
        content.add_widget(Label(text="Year", size_hint_y=None, height=24))
        content.add_widget(self.year_input)

        button_row = BoxLayout(size_hint_y=None, height=44, spacing=10)
        save_button = Button(text="Save", on_release=self.save_member)
        cancel_button = Button(text="Cancel", on_release=lambda *_: self.form_popup.dismiss())
        button_row.add_widget(save_button)
        button_row.add_widget(cancel_button)
        content.add_widget(button_row)

        self.form_popup = Popup(title=title, content=content, size_hint=(0.9, 0.9))
        self.form_popup.open()

    def save_member(self, *_):
        name = self.name_input.text.strip()
        phone = self.phone_input.text.strip()
        amount_text = self.amount_input.text.strip()
        status = self.status_input.text
        month = self.month_input.text
        year = self.year_input.text

        if not name or not phone or not amount_text:
            self.show_message("Please fill name, phone, and amount.")
            return

        try:
            amount = float(amount_text)
        except ValueError:
            self.show_message("Invalid amount. Enter a number.")
            return

        pending_months = 0
        if status == "Pending":
            try:
                pending_months = int(self.pending_months_input.text.strip() or "0")
            except ValueError:
                pending_months = 0
        if self.editing_member_id:
            # If editing a common_template member, insert a month-specific override instead of updating the common record
            if self.original_member_source == "common_template":
                self.cursor.execute(
                    "INSERT INTO members (name, phone, amount, status, month, year, hold, months_pending) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        name,
                        phone,
                        amount,
                        status,
                        self.selected_month,
                        self.selected_year,
                        0,
                        pending_months,
                    ),
                )
            else:
                # For regular month-specific members, update as before
                if self.original_member_month is not None and self.original_member_year is not None:
                    if month != self.original_member_month or year != self.original_member_year:
                        if status == self.original_member_status:
                            status = "Unpaid"
                self.cursor.execute(
                    "UPDATE members SET name=?, phone=?, amount=?, status=?, month=?, year=?, months_pending=? WHERE id=?",
                    (name, phone, amount, status, month, year, pending_months, self.editing_member_id),
                )
        else:
            self.cursor.execute(
                "INSERT INTO members (name, phone, amount, status, month, year, months_pending) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, phone, amount, status, month, year, pending_months),
            )
        self.db.commit()
        self.form_popup.dismiss()
        self.refresh_members()

    def show_message(self, text):
        popup = Popup(title="Info", content=Label(text=text), size_hint=(0.7, 0.4))
        popup.open()

    def load_profile_name(self):
        try:
            with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                value = f.read().strip()
                return value if value else "REHMANI MASJID"
        except Exception:
            return "REHMANI MASJID"

    def save_profile_name_to_file(self):
        try:
            with open(PROFILE_FILE, "w", encoding="utf-8") as f:
                f.write(self.profile_name)
        except Exception:
            pass

    def open_profile_popup(self, *_):
        content = BoxLayout(orientation="vertical", spacing=10, padding=10)
        self.profile_input = TextInput(text=self.profile_name, hint_text="Masjid or admin name", multiline=False, size_hint_y=None, height=40)
        content.add_widget(Label(text="Dashboard heading", size_hint_y=None, height=24))
        content.add_widget(self.profile_input)

        button_row = BoxLayout(size_hint_y=None, height=44, spacing=10)
        save_button = Button(text="Save", on_release=self.save_profile_name)
        cancel_button = Button(text="Cancel", on_release=lambda *_: self.profile_popup.dismiss())
        button_row.add_widget(save_button)
        button_row.add_widget(cancel_button)
        content.add_widget(button_row)

        self.profile_popup = Popup(title="Profile", content=content, size_hint=(0.8, 0.5))
        self.profile_popup.open()

    def save_profile_name(self, *_):
        new_name = self.profile_input.text.strip()
        if new_name:
            self.profile_name = new_name
            self.profile_label.text = self.profile_name
            self.save_profile_name_to_file()
        self.profile_popup.dismiss()

    def show_startup_splash(self):
        splash_content = BoxLayout(orientation="vertical", padding=40, spacing=16)
        title_label = Label(
            text="REHMANI MASJID",
            markup=False,
            font_size=28,
            opacity=0,
            halign="center",
            valign="middle",
            color=self.text_color,
        )
        subtitle_label = Label(
            text="DEVELOP BY AFFAN 18",
            markup=False,
            font_size=16,
            opacity=0,
            halign="center",
            valign="middle",
            color=self.secondary_text_color,
        )
        title_label.bind(size=title_label.setter("text_size"))
        subtitle_label.bind(size=subtitle_label.setter("text_size"))
        splash_content.add_widget(Label(size_hint_y=0.3))
        splash_content.add_widget(title_label)
        splash_content.add_widget(subtitle_label)
        splash_content.add_widget(Label(size_hint_y=0.3))

        self.splash_popup = Popup(
            title="",
            content=splash_content,
            size_hint=(1, 1),
            auto_dismiss=False,
        )
        self.splash_popup.open()

        if hasattr(self, "Animation"):
            anim = self.Animation(opacity=1, font_size=42, duration=2)
            anim += self.Animation(font_size=36, duration=2)
            anim.start(title_label)
            self.Animation(opacity=1, duration=2).start(subtitle_label)

        Clock.schedule_once(lambda *_: self.splash_popup.dismiss(), 4)

    def send_whatsapp_message(self, member):
        phone_digits = "".join(ch for ch in member["phone"] if ch.isdigit())
        if not phone_digits:
            self.show_message("Please enter a valid phone number for WhatsApp reminders.")
            return
        message_month = self.selected_month if member["month"] == "Common" else member["month"]
        message_year = self.selected_year if member["month"] == "Common" else member["year"]
        message = (
            f"Hello {member['name']} your receipt of {message_month} {message_year} is pending of {format_money(member['amount'])} please pay as soon as possible. REHMANI MASJID\n"
            "For any query contact Abdullah Khan or committee of masjid."
        )
        encoded = urllib.parse.quote(message)
        url = f"https://api.whatsapp.com/send?phone={phone_digits}&text={encoded}"
        webbrowser.open(url)

    def import_members_txt(self):
        try:
            with open("members.txt", "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            self.show_message("No members.txt found to import.")
            return
        imported = 0
        for line in lines:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 3:
                continue
            name, phone, amount = parts[0], parts[1], parts[2]
            try:
                amount_f = float(amount)
            except ValueError:
                amount_f = 0.0
            # default status Unpaid, use current month/year
            self.cursor.execute(
                "INSERT INTO members (name, phone, amount, status, month, year, months_pending) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, phone, amount_f, "Unpaid", self.selected_month, self.selected_year, 0),
            )
            imported += 1
        self.db.commit()
        self.show_message(f"Imported {imported} members from members.txt")
        self.refresh_members()

    def import_members_csv(self):
        try:
            with open("members.csv", "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except FileNotFoundError:
            self.show_message("No members.csv found to import.")
            return
        except Exception:
            self.show_message("Unable to read members.csv. Check file format.")
            return

        imported = 0
        for row in rows:
            if not row:
                continue
            name = (row.get("name") or row.get("Name") or "").strip()
            phone = (row.get("phone") or row.get("Phone") or "").strip()
            amount_text = (row.get("amount") or row.get("Amount") or "").strip()
            status = (row.get("status") or row.get("Status") or "Unpaid").strip() or "Unpaid"
            month = (row.get("month") or row.get("Month") or self.selected_month).strip() or self.selected_month
            year = (row.get("year") or row.get("Year") or self.selected_year).strip() or self.selected_year
            hold_field = (row.get("hold") or row.get("Hold") or "0").strip().lower()
            hold = 1 if hold_field in ("1", "true", "yes", "y") else 0
            months_pending_text = (row.get("months_pending") or row.get("Months Pending") or row.get("months pending") or "0").strip()
            try:
                months_pending = int(months_pending_text) if months_pending_text else 0
            except ValueError:
                months_pending = 0

            if not name or not phone:
                continue
            try:
                amount_f = float(amount_text) if amount_text else 0.0
            except ValueError:
                amount_f = 0.0

            self.cursor.execute(
                "INSERT INTO members (name, phone, amount, status, month, year, hold, months_pending) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (name, phone, amount_f, status, month, year, hold, months_pending),
            )
            imported += 1

        self.db.commit()
        self.show_message(f"Imported {imported} members from members.csv")
        self.refresh_members()

    def export_members_csv(self):
        members = self.query_members(self.selected_year, self.selected_month, self.selected_status)
        if not members:
            self.show_message("No records available to export for the selected filter.")
            return

        try:
            with open("members_export.csv", "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["name", "phone", "amount", "status", "month", "year", "hold", "months_pending"])
                for member in members:
                    writer.writerow([
                        member["name"],
                        member["phone"],
                        member["amount"],
                        member["status"],
                        member["month"],
                        member["year"],
                        int(member["hold"]),
                        member.get("months_pending", 0),
                    ])
        except Exception:
            self.show_message("Unable to write members_export.csv. Check file permissions.")
            return

        self.show_message(f"Exported {len(members)} members to members_export.csv")
        self.refresh_members()

    def build_print_preview_html(self, members):
        title = f"Masjid Receipts - {self.selected_month} {self.selected_year}"
        rows = "\n".join(
            f"<tr><td>{index}</td><td>{member['name']}</td><td>{member['phone']}</td><td>{format_money(member['amount'])}{' (' + format_money(member['amount'] * member['months_pending']) + ')' if member['status'] == 'Pending' and member['months_pending'] else ''}</td><td>{member['status']}</td><td>{member['hold'] and 'Yes' or 'No'}</td></tr>"
            for index, member in enumerate(members, start=1)
        )
        month_total, year_total = self.calculate_totals(self.selected_year, self.selected_month)
        return f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\">
<title>{title}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; color: #222; position: relative; }}
.header {{ padding-bottom: 8px; border-bottom: 1px solid #ccc; margin-bottom: 16px; }}
h1 {{ margin: 0; display: inline-block; }}
.header-note {{ display: inline-block; float: right; font-size: 16px; color: #000; margin: 0; margin-top: 6px; font-weight: 600; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
th, td {{ border: 1px solid #999; padding: 8px; text-align: left; }}
th {{ background: #f0f0f0; }}
.summary {{ margin-top: 18px; }}
button.print-button {{ margin-top: 16px; padding: 10px 16px; font-size: 14px; }}
</style>
</head>
<body>
<div class=\"header\">
<h1>{title}</h1>
<p class=\"header-note\">develop by AFFAN18</p>
</div>
<p>Print preview for selected filter, including {self.selected_status} records.</p>
<table>
<thead>
<tr><th>#</th><th>Name</th><th>Phone</th><th>Amount</th><th>Status</th><th>Hold</th></tr>
</thead>
<tbody>
{rows}
</tbody>
</table>
<div class=\"summary\">
<p><strong>Month Total:</strong> {format_money(month_total)}</p>
<p><strong>Year Total:</strong> {format_money(year_total)}</p>
</div>
<button class=\"print-button\" onclick=\"window.print()\">Print</button>
</body>
</html>
"""

    def open_print_preview(self):
        members = self.query_members(self.selected_year, self.selected_month, self.selected_status)
        if not members:
            self.show_message("No records available for print preview.")
            return
        html = self.build_print_preview_html(members)
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as tmp:
                tmp.write(html)
                preview_path = tmp.name
        except Exception:
            self.show_message("Could not generate print preview.")
            return
        webbrowser.open(f"file://{preview_path}")

    def print_members(self):
        members = self.query_members(self.selected_year, self.selected_month, self.selected_status)
        if not members:
            self.show_message("No records available to print.")
            return
        html = self.build_print_preview_html(members)
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as tmp:
                tmp.write(html)
                print_path = tmp.name
        except Exception:
            self.show_message("Could not prepare the print file.")
            return

        if os.name == "nt":
            try:
                os.startfile(print_path, "print")
                return
            except Exception:
                pass

        print_program = None
        for cmd in ("lp", "lpr"):
            if shutil.which(cmd):
                print_program = cmd
                break

        if print_program:
            try:
                subprocess.run([print_program, print_path], check=True)
                return
            except Exception:
                pass

        webbrowser.open(f"file://{print_path}")
        self.show_message("Preview opened in browser. Use the browser print dialog to print.")


if __name__ == "__main__":
    MasjidReceiptManagerApp().run()
