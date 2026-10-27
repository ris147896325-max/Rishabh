import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import csv
from datetime import datetime

# ─────────────────────────── DATABASE ───────────────────────────
class Database:
    def __init__(self, db_name="students.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roll_no TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                age INTEGER,
                gender TEXT,
                course TEXT,
                email TEXT,
                phone TEXT
            )
        """)
        self.conn.commit()

    def add(self, data):
        self.cursor.execute("""
            INSERT INTO students (roll_no, name, age, gender, course, email, phone)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, data)
        self.conn.commit()

    def update(self, sid, data):
        self.cursor.execute("""
            UPDATE students SET roll_no=?, name=?, age=?, gender=?,
            course=?, email=?, phone=? WHERE id=?
        """, (*data, sid))
        self.conn.commit()

    def delete(self, sid):
        self.cursor.execute("DELETE FROM students WHERE id=?", (sid,))
        self.conn.commit()

    def fetch_all(self):
        self.cursor.execute("SELECT * FROM students ORDER BY id DESC")
        return self.cursor.fetchall()

    def search(self, keyword):
        self.cursor.execute("""
            SELECT * FROM students
            WHERE name LIKE ? OR roll_no LIKE ?
            ORDER BY id DESC
        """, (f"%{keyword}%", f"%{keyword}%"))
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()


# ─────────────────────────── GUI ───────────────────────────
class StudentApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Student Management System")
        self.root.geometry("1000x650")
        self.root.configure(bg="#f0f4f8")
        self.db = Database()
        self.selected_id = None

        self.build_ui()
        self.load_data()

    # ---------- UI BUILD ----------
    def build_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#1e3a8a", height=70)
        header.pack(fill="x")
        tk.Label(
            header, text="🎓 Student Management System",
            font=("Segoe UI", 20, "bold"),
            bg="#1e3a8a", fg="white"
        ).pack(pady=15)

        # Main container
        main = tk.Frame(self.root, bg="#f0f4f8")
        main.pack(fill="both", expand=True, padx=15, pady=10)

        # ----- LEFT: Form -----
        form = tk.LabelFrame(
            main, text=" Student Details ",
            font=("Segoe UI", 11, "bold"),
            bg="white", fg="#1e3a8a", padx=15, pady=10
        )
        form.pack(side="left", fill="y", padx=(0, 10))

        self.entries = {}
        fields = [
            ("Roll No", "roll_no"),
            ("Name", "name"),
            ("Age", "age"),
            ("Gender", "gender"),
            ("Course", "course"),
            ("Email", "email"),
            ("Phone", "phone"),
        ]

        for i, (label, key) in enumerate(fields):
            tk.Label(form, text=label, font=("Segoe UI", 10),
                     bg="white", anchor="w").grid(row=i, column=0, sticky="w", pady=5)

            if key == "gender":
                var = tk.StringVar(value="Male")
                cb = ttk.Combobox(form, textvariable=var,
                                  values=["Male", "Female", "Other"],
                                  state="readonly", width=25)
                cb.grid(row=i, column=1, pady=5, padx=5)
                self.entries[key] = var
            else:
                entry = tk.Entry(form, font=("Segoe UI", 10), width=28)
                entry.grid(row=i, column=1, pady=5, padx=5)
                self.entries[key] = entry

        # Buttons
        btn_frame = tk.Frame(form, bg="white")
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=15)

        self.make_button(btn_frame, "➕ Add", "#16a34a", self.add_student).grid(row=0, column=0, padx=4, pady=4)
        self.make_button(btn_frame, "✏ Update", "#2563eb", self.update_student).grid(row=0, column=1, padx=4, pady=4)
        self.make_button(btn_frame, "🗑 Delete", "#dc2626", self.delete_student).grid(row=1, column=0, padx=4, pady=4)
        self.make_button(btn_frame, "🧹 Clear", "#6b7280", self.clear_form).grid(row=1, column=1, padx=4, pady=4)

        # ----- RIGHT: Table + Search -----
        right = tk.Frame(main, bg="#f0f4f8")
        right.pack(side="right", fill="both", expand=True)

        # Search bar
        search_frame = tk.Frame(right, bg="#f0f4f8")
        search_frame.pack(fill="x", pady=(0, 8))

        tk.Label(search_frame, text="🔍 Search:", font=("Segoe UI", 10, "bold"),
                 bg="#f0f4f8").pack(side="left", padx=(0, 5))

        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *a: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var,
                 font=("Segoe UI", 10), width=30).pack(side="left")

        self.make_button(search_frame, "⬇ Export CSV", "#0e7490",
                         self.export_csv).pack(side="right")

        # Table
        table_frame = tk.Frame(right)
        table_frame.pack(fill="both", expand=True)

        cols = ("id", "roll_no", "name", "age", "gender", "course", "email", "phone")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=20)

        headings = ["ID", "Roll No", "Name", "Age", "Gender", "Course", "Email", "Phone"]
        widths = [40, 80, 120, 50, 70, 100, 160, 100]

        for c, h, w in zip(cols, headings, widths):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor="center")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # Style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", font=("Segoe UI", 9), rowheight=26)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"),
                        background="#1e3a8a", foreground="white")

    def make_button(self, parent, text, color, command):
        return tk.Button(
            parent, text=text, command=command,
            bg=color, fg="white",
            font=("Segoe UI", 10, "bold"),
            relief="flat", padx=15, pady=6,
            cursor="hand2", activebackground=color
        )

    # ---------- DATA OPS ----------
    def get_form_data(self):
        data = []
        for key in ["roll_no", "name", "age", "gender", "course", "email", "phone"]:
            val = self.entries[key].get().strip() if key != "gender" else self.entries[key].get()
            data.append(val)
        return data

    def validate(self, data):
        roll, name, age, gender, course, email, phone = data
        if not roll or not name:
            messagebox.showwarning("Validation", "Roll No and Name are required!")
            return False
        if age and not age.isdigit():
            messagebox.showwarning("Validation", "Age must be a number!")
            return False
        return True

    def add_student(self):
        data = self.get_form_data()
        if not self.validate(data):
            return
        try:
            self.db.add(data)
            messagebox.showinfo("Success", "Student added successfully!")
            self.clear_form()
            self.load_data()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Roll No already exists!")

    def update_student(self):
        if not self.selected_id:
            messagebox.showwarning("Warning", "Select a student to update.")
            return
        data = self.get_form_data()
        if not self.validate(data):
            return
        try:
            self.db.update(self.selected_id, data)
            messagebox.showinfo("Success", "Student updated successfully!")
            self.clear_form()
            self.load_data()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Roll No already exists!")

    def delete_student(self):
        if not self.selected_id:
            messagebox.showwarning("Warning", "Select a student to delete.")
            return
        if messagebox.askyesno("Confirm", "Delete this student?"):
            self.db.delete(self.selected_id)
            self.clear_form()
            self.load_data()

    def clear_form(self):
        for key, widget in self.entries.items():
            if key == "gender":
                widget.set("Male")
            else:
                widget.delete(0, tk.END)
        self.selected_id = None
        self.tree.selection_remove(self.tree.selection())

    # ---------- TABLE ----------
    def load_data(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for row in self.db.fetch_all():
            self.tree.insert("", "end", values=row)

    def search_data(self):
        keyword = self.search_var.get().strip()
        for row in self.tree.get_children():
            self.tree.delete(row)
        rows = self.db.search(keyword) if keyword else self.db.fetch_all()
        for row in rows:
            self.tree.insert("", "end", values=row)

    def on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        self.selected_id = values[0]

        keys = ["roll_no", "name", "age", "gender", "course", "email", "phone"]
        for i, key in enumerate(keys):
            val = values[i + 1]
            if key == "gender":
                self.entries[key].set(val)
            else:
                self.entries[key].delete(0, tk.END)
                self.entries[key].insert(0, val)

    # ---------- EXPORT ----------
    def export_csv(self):
        rows = self.db.fetch_all()
        if not rows:
            messagebox.showinfo("Info", "No data to export.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"students_{datetime.now():%Y%m%d_%H%M%S}.csv"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Roll No", "Name", "Age", "Gender",
                             "Course", "Email", "Phone"])
            writer.writerows(rows)
        messagebox.showinfo("Success", f"Exported to:\n{path}")


# ─────────────────────────── RUN ───────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = StudentApp(root)
    root.mainloop()