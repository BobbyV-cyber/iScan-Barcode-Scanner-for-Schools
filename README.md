[rename_photo.py](https://github.com/user-attachments/files/33970107/rename_photo.py)
import os

# Your specific photos directory
folder_directory = (
    r"C:\Users\malig\OneDrive\Desktop\MINHS Attendance System\photos"
)


def update_to_four_digits(folder_path):
    files = sorted(
        [f for f in os.listdir(folder_path) if f.lower().endswith(".jpg")]
    )

    if not files:
        print("No .jpg files found in the directory.")
        return

    count = 0
    for filename in files:
        # Check if file follows the MINHS-LNR- pattern
        if filename.startswith("MINHS-LNR-"):
            # Extract the numeric part before .jpg
            base_name, ext = os.path.splitext(filename)
            number_part = base_name.replace("MINHS-LNR-", "")

            # Process only if numeric
            if number_part.isdigit():
                num = int(number_part)
                # Form 4-digit zero-padded filename
                new_filename = f"MINHS-LNR-{num:04d}{ext.lower()}"

                old_file = os.path.join(folder_path, filename)
                new_file = os.path.join(folder_path, new_filename)

                if old_file != new_file:
                    os.rename(old_file, new_file)
                    print(f"Renamed: {filename} -> {new_filename}")
                    count += 1

    print(f"\nDone! Successfully updated {count} files to 4-digit formatting.")


update_to_four_digits(folder_directory)
