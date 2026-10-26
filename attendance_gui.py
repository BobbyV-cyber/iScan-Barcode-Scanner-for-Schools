import tkinter as tk
import sqlite3
from datetime import datetime

# ==========================================
# MINHS ATTENDANCE MONITOR - GUI TEST
# ==========================================

BASE_DIR = r"C:\Users\malig\OneDrive\Desktop\MINHS Attendance System"
DB_PATH = BASE_DIR + r"\database\minhs_attendance.db"


class AttendanceGUI:

    def __init__(self, root):
        self.root = root

        self.root.title("MINHS Attendance Monitor")
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg="#111111")

        # -----------------------------
        # Title
        # -----------------------------
        self.title_label = tk.Label(
            root,
            text="MINHS ATTENDANCE MONITOR",
            font=("Arial", 32, "bold"),
            fg="white",
            bg="#111111"
        )
        self.title_label.pack(pady=(40, 20))

        # -----------------------------
        # Instruction
        # -----------------------------
        self.instruction_label = tk.Label(
            root,
            text="SCAN LEARNER BARCODE",
            font=("Arial", 24, "bold"),
            fg="white",
            bg="#111111"
        )
        self.instruction_label.pack(pady=20)

        # -----------------------------
        # Learner name
        # -----------------------------
        self.name_label = tk.Label(
            root,
            text="Ready for scanning...",
            font=("Arial", 40, "bold"),
            fg="white",
            bg="#111111"
        )
        self.name_label.pack(pady=30)

        # -----------------------------
        # Learner information
        # -----------------------------
        self.info_label = tk.Label(
            root,
            text="",
            font=("Arial", 24),
            fg="white",
            bg="#111111"
        )
        self.info_label.pack(pady=10)

        # -----------------------------
        # Attendance result
        # -----------------------------
        self.result_label = tk.Label(
            root,
            text="",
            font=("Arial", 34, "bold"),
            fg="white",
            bg="#111111"
        )
        self.result_label.pack(pady=30)

        # -----------------------------
        # Time
        # -----------------------------
        self.time_label = tk.Label(
            root,
            text="",
            font=("Arial", 22),
            fg="white",
            bg="#111111"
        )
        self.time_label.pack(pady=10)

        # -----------------------------
        # Hidden barcode input
        # -----------------------------
        self.scan_entry = tk.Entry(
            root,
            font=("Arial", 1),
            fg="#111111",
            bg="#111111",
            insertbackground="#111111",
            borderwidth=0
        )

        self.scan_entry.place(
            x=0,
            y=0,
            width=1,
            height=1
        )

        self.scan_entry.focus_set()

        self.scan_entry.bind(
            "<Return>",
            self.process_scan
        )

        # Keep scanner input focused
        self.root.bind(
            "<Button-1>",
            self.refocus_scanner
        )

        # ESC exits fullscreen
        self.root.bind(
            "<Escape>",
            self.exit_fullscreen
        )

        self.update_clock()

    # ==========================================
    # Keep scanner focused
    # ==========================================

    def refocus_scanner(self, event=None):
        self.scan_entry.focus_set()

    # ==========================================
    # Process barcode
    # ==========================================

    def process_scan(self, event=None):

        barcode = self.scan_entry.get().strip()

        self.scan_entry.delete(0, tk.END)

        if not barcode:
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT first_name,
                   middle_name,
                   last_name,
                   grade_level,
                   section
            FROM learners
            WHERE barcode = ?
              AND status = 'ACTIVE'
        """, (barcode,))

        learner = cursor.fetchone()

        conn.close()

        if learner:

            first, middle, last, grade, section = learner

            middle = middle or ""

            full_name = " ".join(
                [first, middle, last]
            ).strip()

            self.name_label.config(
                text=full_name
            )

            self.info_label.config(
                text=f"Grade {grade}  •  Section {section}\n"
                     f"Barcode: {barcode}"
            )

            self.result_label.config(
                text="✓ LEARNER IDENTIFIED",
                fg="lightgreen"
            )

        else:

            self.name_label.config(
                text="UNKNOWN BARCODE"
            )

            self.info_label.config(
                text=barcode
            )

            self.result_label.config(
                text="✗ LEARNER NOT FOUND",
                fg="red"
            )

        self.scan_entry.focus_set()

    # ==========================================
    # Clock
    # ==========================================

    def update_clock(self):

        current_time = datetime.now().strftime(
            "%A, %B %d, %Y  |  %I:%M:%S %p"
        )

        self.time_label.config(
            text=current_time
        )

        self.root.after(
            1000,
            self.update_clock
        )

    # ==========================================
    # Exit
    # ==========================================

    def exit_fullscreen(self, event=None):
        self.root.attributes("-fullscreen", False)


# ==========================================
# START APPLICATION
# ==========================================

root = tk.Tk()

app = AttendanceGUI(root)

root.mainloop()