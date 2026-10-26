import tkinter as tk
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from PIL import Image, ImageTk
from learner_photo_loader import load_photo


# ============================================================
# PROJECT / DATABASE
# ============================================================

PROJECT_FOLDER = Path(__file__).resolve().parent.parent
DATABASE_FILE = PROJECT_FOLDER / "database" / "minhs_attendance.db"


# ============================================================
# ATTENDANCE SETTINGS
# ============================================================

AM_IN_START = "05:00:00"
AM_IN_END = "08:30:00"

AM_OUT_START = "11:00:00"
AM_OUT_END = "13:00:00"

PM_IN_START = "12:00:00"
PM_IN_END = "13:30:00"

PM_OUT_START = "15:30:00"
PM_OUT_END = "18:00:00"

DUPLICATE_MINUTES = 5

# ============================================================
# DEVELOPMENT TEST MODE
# ============================================================

TEST_MODE = False

TEST_TIME = "16:30:00"

# ============================================================
# DATABASE FUNCTIONS
# ============================================================

def connect_database():
    return sqlite3.connect(DATABASE_FILE)


def find_learner(barcode):
    connection = connect_database()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            barcode,
            first_name,
            middle_name,
            last_name,
            grade_level,
            section,
            status
        FROM learners
        WHERE barcode = ?

    """, (barcode,))

    learner = cursor.fetchone()

    connection.close()

    return learner


def get_today_records(learner_id, today):
    connection = connect_database()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            attendance_time,
            transaction_type
        FROM attendance
        WHERE learner_id = ?
          AND attendance_date = ?
        ORDER BY id
    """, (learner_id, today))

    records = cursor.fetchall()

    connection.close()

    return records


def record_attendance(
    learner_id,
    today,
    current_time,
    transaction_type
):
    connection = connect_database()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO attendance
            (
                learner_id,
                attendance_date,
                attendance_time,
                transaction_type
            )
            VALUES (?, ?, ?, ?)
        """, (
            learner_id,
            today,
            current_time,
            transaction_type
        ))
        connection.commit()
    except Exception:
        try:
            connection.rollback()
        except sqlite3.Error:
            pass
        raise
    finally:
        connection.close()


# ============================================================
# TIME / ATTENDANCE LOGIC
# ============================================================

def time_is_between(current_time, start_time, end_time):

    current = datetime.strptime(
        current_time,
        "%H:%M:%S"
    ).time()

    start = datetime.strptime(
        start_time,
        "%H:%M:%S"
    ).time()

    end = datetime.strptime(
        end_time,
        "%H:%M:%S"
    ).time()

    return start <= current <= end


def determine_transaction(current_time, records):

    completed_transactions = [
        record[2]
        for record in records
    ]

    # AM IN
    if "AM IN" not in completed_transactions:

        if time_is_between(
            current_time,
            AM_IN_START,
            AM_IN_END
        ):
            return "AM IN"

    # AM OUT
    if "AM IN" in completed_transactions:

        if "AM OUT" not in completed_transactions:

            if time_is_between(
                current_time,
                AM_OUT_START,
                AM_OUT_END
            ):
                return "AM OUT"

    # PM IN
    if "AM OUT" in completed_transactions:

        if "PM IN" not in completed_transactions:

            if time_is_between(
                current_time,
                PM_IN_START,
                PM_IN_END
            ):
                return "PM IN"

    # PM OUT
    if "PM IN" in completed_transactions:

        if "PM OUT" not in completed_transactions:

            if time_is_between(
                current_time,
                PM_OUT_START,
                PM_OUT_END
            ):
                return "PM OUT"

    return None


def process_attendance_scan(barcode):

    barcode = barcode.strip()

    learner = find_learner(barcode)

    # --------------------------------------------------------
    # UNKNOWN BARCODE
    # --------------------------------------------------------

    if learner is None:
        return {
            "success": False,
            "type": "UNKNOWN",
            "message": "LEARNER NOT FOUND",
            "barcode": barcode
        }

    if learner[7] != "ACTIVE":
        return {
            "success": False,
            "type": "INACTIVE",
            "message": "LEARNER INACTIVE",
            "barcode": barcode
        }


    # --------------------------------------------------------
    # LEARNER INFORMATION
    # --------------------------------------------------------

    learner_id = learner[0]
    learner_barcode = learner[1]
    first_name = learner[2]
    middle_name = learner[3] or ""
    last_name = learner[4]
    grade_level = learner[5]
    section = learner[6]

    full_name = " ".join(
        part for part in [
            first_name,
            middle_name,
            last_name
        ]
        if part
    )

    # --------------------------------------------------------
    # CURRENT DATE / TIME
    # --------------------------------------------------------

    now = datetime.now()

    today = now.strftime("%Y-%m-%d")

    if TEST_MODE:
        current_time_database = TEST_TIME

        current_time_display = datetime.strptime(
            TEST_TIME,
            "%H:%M:%S"
        ).strftime("%I:%M:%S %p")

    else:
        current_time_database = now.strftime("%H:%M:%S")

        current_time_display = now.strftime(
            "%I:%M:%S %p"
        )

    # --------------------------------------------------------
    # TODAY'S RECORDS
    # --------------------------------------------------------

    records = get_today_records(
        learner_id,
        today
    )

    # --------------------------------------------------------
    # DUPLICATE PROTECTION
    # --------------------------------------------------------

    if len(records) > 0:

        last_record = records[-1]

        last_time_string = last_record[1]

        last_timestamp = datetime.strptime(
            f"{today} {last_time_string}",
            "%Y-%m-%d %H:%M:%S"
        )

        current_timestamp = datetime.strptime(
            f"{today} {current_time_database}",
            "%Y-%m-%d %H:%M:%S"
        )

        time_difference = current_timestamp - last_timestamp

        if timedelta(0) <= time_difference < timedelta(
            minutes=DUPLICATE_MINUTES
        ):

            return {
                "success": False,
                "type": "DUPLICATE",
                "message": "DUPLICATE SCAN",
                "name": full_name,
                "grade": grade_level,
                "section": section,
                "barcode": learner_barcode,
                "previous_time": last_time_string,
                "current_time": current_time_display
            }

    # --------------------------------------------------------
    # DETERMINE ATTENDANCE TRANSACTION
    # --------------------------------------------------------

    transaction_type = determine_transaction(
        current_time_database,
        records
    )

    # --------------------------------------------------------
    # INVALID TIME / WRONG SEQUENCE
    # --------------------------------------------------------

    if transaction_type is None:

        completed = [
            record[2]
            for record in records
        ]

        if len(completed) == 0:
            expected = "AM IN"
        elif "AM IN" not in completed:
            expected = "AM IN"
        elif "AM OUT" not in completed:
            expected = "AM OUT"
        elif "PM IN" not in completed:
            expected = "PM IN"
        elif "PM OUT" not in completed:
            expected = "PM OUT"
        else:
            expected = "COMPLETED"

        return {
            "success": False,
            "type": "INVALID",
            "message": "SCAN NOT ACCEPTED",
            "name": full_name,
            "grade": grade_level,
            "section": section,
            "barcode": learner_barcode,
            "current_time": current_time_display,
            "expected": expected
        }

    # --------------------------------------------------------
    # SAVE ATTENDANCE
    # --------------------------------------------------------

    record_attendance(
        learner_id,
        today,
        current_time_database,
        transaction_type
    )

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    updated_records = get_today_records(
        learner_id,
        today
    )

    transactions_today = [
        record[2]
        for record in updated_records
    ]

    return {
        "success": True,
        "type": "SUCCESS",
        "message": "ATTENDANCE RECORDED",
        "name": full_name,
        "grade": grade_level,
        "section": section,
        "barcode": learner_barcode,
        "transaction": transaction_type,
        "current_time": current_time_display,
        "transactions_today": transactions_today
    }

# ============================================================
# GUI
# ============================================================

class AttendanceSystemGUI:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "MINHS Attendance Monitoring System"
        )

        self.root.attributes(
            "-fullscreen",
            True
        )

        self.root.configure(
            bg="#111111"
        )


        # ----------------------------------------------------
        # TITLE
        # ----------------------------------------------------

        self.title_label = tk.Label(
            root,
            text="MINHS ATTENDANCE MONITORING SYSTEM",
            font=("Arial", 32, "bold"),
            fg="white",
            bg="#111111"
        )

        self.title_label.pack(
            pady=(40, 20)
        )


        # ----------------------------------------------------
        # INSTRUCTION
        # ----------------------------------------------------

        self.instruction_label = tk.Label(
            root,
            text="SCAN LEARNER BARCODE",
            font=("Arial", 24, "bold"),
            fg="white",
            bg="#111111"
        )

        self.instruction_label.pack(
            pady=20
        )


        # ----------------------------------------------------
        # LEARNER DISPLAY: PHOTO LEFT, DETAILS RIGHT
        # ----------------------------------------------------

        # ----------------------------------------------------
        # HORIZONTAL DIVIDER ABOVE THE LEARNER DISPLAY
        # ----------------------------------------------------
        self.horizontal_divider = tk.Frame(
            root, bg="#777777", height=2
        )
        self.horizontal_divider.pack(
            side="top", fill="x", padx=40, pady=(0, 8)
        )


        self.display_frame = tk.Frame(root, bg="#111111")
        self.display_frame.pack(
            fill="both", expand=True, padx=40, pady=10
        )

        self.photo_frame = tk.Frame(
            self.display_frame, bg="#222222", width=380,
            highlightbackground="#777777", highlightthickness=3, bd=0
        )
        self.photo_frame.pack(side="left", fill="y", padx=(0, 35), pady=12)
        self.photo_frame.pack_propagate(False)

        self.photo_label = tk.Label(
            self.photo_frame, text="LEARNER PHOTO",
            font=("Arial", 16, "bold"), fg="#bbbbbb", bg="#222222",
            anchor="center", padx=8, pady=8
        )
        self.photo_label.pack(expand=True, anchor="center")
        self.current_photo = None

        self.details_frame = tk.Frame(self.display_frame, bg="#111111")
        self.details_frame.pack(side="left", fill="both", expand=True)

        self.name_label = tk.Label(
            self.details_frame, text="Ready for scanning...",
            font=("Arial", 32, "bold"), fg="white", bg="#111111",
            wraplength=850, justify="left", anchor="w"
        )
        self.name_label.pack(fill="x", anchor="w", pady=(10, 18))

        self.info_label = tk.Label(
            self.details_frame, text="", font=("Arial", 20),
            fg="white", bg="#111111", wraplength=850,
            justify="left", anchor="w"
        )
        self.info_label.pack(fill="x", anchor="w", pady=8)

        self.result_label = tk.Label(
            self.details_frame, text="", font=("Arial", 28, "bold"),
            fg="white", bg="#111111", wraplength=850,
            justify="left", anchor="w"
        )
        self.result_label.pack(fill="x", anchor="w", pady=12)

        self.attendance_label = tk.Label(
            self.details_frame, text="", font=("Arial", 18),
            fg="white", bg="#111111", wraplength=850,
            justify="left", anchor="w"
        )
        self.attendance_label.pack(fill="x", anchor="w", pady=8)

        self.time_label = tk.Label(
            root, text="", font=("Arial", 18),
            fg="white", bg="#111111"
        )
        self.time_label.pack(side="bottom", pady=10)

        # ----------------------------------------------------
        # DEVELOPER LOGO: BOTTOM-RIGHT
        # ----------------------------------------------------
        logo_path = (
            Path(__file__).resolve().parent.parent
            / "developer_logo"
            / "dravenx_rounded.png"
        )
        with Image.open(logo_path) as logo_image:
            logo_image = logo_image.convert("RGBA")
            logo_image.thumbnail((76, 61), Image.Resampling.LANCZOS)
            self.developer_logo_photo = ImageTk.PhotoImage(logo_image)

        self.developer_logo_label = tk.Label(
            root,
            image=self.developer_logo_photo,
            bg="#111111",
            bd=0,
            highlightthickness=0
        )
        self.developer_logo_label.place(
            relx=1.0, rely=1.0, x=-18, y=-12, anchor="se"
        )


        # ----------------------------------------------------
        # HIDDEN SCANNER INPUT
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # KEEP SCANNER FOCUSED
        # ----------------------------------------------------

        self.root.bind(
            "<Button-1>",
            self.refocus_scanner
        )

        self.root.bind(
            "<Escape>",
            self.exit_fullscreen
        )


        # ----------------------------------------------------
        # CLOCK
        # ----------------------------------------------------

        self.update_clock()


    # ========================================================
    # SCANNER FOCUS
    # ========================================================

    def refocus_scanner(self, event=None):

        self.scan_entry.focus_set()


    def show_learner_photo(self, scanned_barcode):
        """Display a matching photo without interrupting attendance processing."""
        try:
            photo = load_photo(scanned_barcode)
        except Exception as exc:
            print(f"Photo display warning: {exc}")
            photo = None

        if photo is None:
            self.photo_label.config(image="", text="LEARNER PHOTO")
            self.current_photo = None
            return False

        self.photo_label.config(image=photo, text="")
        self.current_photo = photo
        return True


    # ========================================================
    # PROCESS SCAN
    # ========================================================

    def process_scan(self, event=None):

        barcode = self.scan_entry.get().strip()

        self.scan_entry.delete(
            0,
            tk.END
        )

        if not barcode:
            return

        # Photo lookup is read-only and independent of attendance processing.
        self.show_learner_photo(barcode)

        # Send barcode to attendance engine; handle database errors safely.
        try:
            result = process_attendance_scan(barcode)
        except sqlite3.Error as exc:
            print("Attendance database error:", type(exc).__name__)
            self.name_label.config(text="ATTENDANCE SYSTEM ERROR")
            self.info_label.config(text="Scan status could not be confirmed.")
            self.result_label.config(text="? DATABASE ERROR", fg="red")
            self.attendance_label.config(
                text="Ask school staff to verify attendance before retrying."
            )
            self.scan_entry.focus_set()
            return


        # ----------------------------------------------------
        # UNKNOWN BARCODE
        # ----------------------------------------------------

        if result["type"] == "UNKNOWN":

            self.name_label.config(
                text="UNKNOWN BARCODE"
            )

            self.info_label.config(
                text=result["barcode"]
            )

            self.result_label.config(
                text="âœ— LEARNER NOT FOUND",
                fg="red"
            )

            self.attendance_label.config(
                text=""
            )


        # ----------------------------------------------------
        # DUPLICATE
        # ----------------------------------------------------

        elif result["type"] == "DUPLICATE":

            self.name_label.config(
                text=result["name"]
            )

            self.info_label.config(
                text=(
                    f"Grade {result['grade']}  â€¢  "
                    f"Section {result['section']}\n"
                    f"Barcode: {result['barcode']}"
                )
            )

            self.result_label.config(
                text="âš  DUPLICATE SCAN",
                fg="orange"
            )

            self.attendance_label.config(
                text=(
                    f"Previous scan: "
                    f"{result['previous_time']}\n"
                    f"Current time: "
                    f"{result['current_time']}\n"
                    f"Please wait at least "
                    f"{DUPLICATE_MINUTES} minutes."
                )
            )


        # ----------------------------------------------------
        # INVALID TIME / SEQUENCE
        # ----------------------------------------------------

        elif result["type"] == "INVALID":

            self.name_label.config(
                text=result["name"]
            )

            self.info_label.config(
                text=(
                    f"Grade {result['grade']}  â€¢  "
                    f"Section {result['section']}\n"
                    f"Barcode: {result['barcode']}"
                )
            )

            self.result_label.config(
                text="âœ— SCAN NOT ACCEPTED",
                fg="red"
            )

            self.attendance_label.config(
                text=(
                    f"Current time: "
                    f"{result['current_time']}\n"
                    f"Expected: "
                    f"{result['expected']}"
                )
            )


        # ----------------------------------------------------
        # SUCCESSFUL ATTENDANCE
        # ----------------------------------------------------

        elif result["type"] == "SUCCESS":

            self.name_label.config(
                text=result["name"]
            )

            self.info_label.config(
                text=(
                    f"Grade {result['grade']}  â€¢  "
                    f"Section {result['section']}\n"
                    f"Barcode: {result['barcode']}"
                )
            )

            self.result_label.config(
                text=(
                    f"âœ“ {result['transaction']}"
                ),
                fg="lightgreen"
            )

            sequence = " â†’ ".join(
                result["transactions_today"]
            )

            self.attendance_label.config(
                text=(
                    f"Time: {result['current_time']}\n"
                    f"Today's attendance: {sequence}"
                )
            )


        # ----------------------------------------------------
        # RESTORE SCANNER FOCUS
        # ----------------------------------------------------

        self.scan_entry.focus_set()


    # ========================================================
    # CLOCK
    # ========================================================

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


    # ========================================================
    # EXIT FULLSCREEN
    # ========================================================

    def exit_fullscreen(self, event=None):

        self.root.attributes(
            "-fullscreen",
            False
        )


# ============================================================
# START APPLICATION
# ============================================================

root = tk.Tk()

app = AttendanceSystemGUI(
    root
)

root.mainloop()


