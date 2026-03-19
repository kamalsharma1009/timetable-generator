# EduSync: Intelligent Timetable Generator

A modern, robust web application built to automatically generate clash-free academic timetables using a powerful Genetic Algorithm. Designed specifically to adhere to the formatting and complex rules of **DKTE Society's Yashwantrao Chavan Polytechnic**, this system allows administrators to manage departments, faculties, subjects, and rooms while completely automating the scheduling process.

## 🚀 Key Features

- **Algorithmic Scheduling**: Utilizes a custom Genetic Algorithm to automatically generate clash-free timetables handling complex constraints like shared labs, faculty overlap, and parallel practical batches.
- **Institutional Print Formatting**: Generates an exact pixel-perfect A4 Landscape print layout of the timetable, strictly matching the physical DKTE polytechnic format (complete with logos, signature blocks, and mapping tables).
- **Excel Export**: Download the generated timetable instantly as an `.xlsx` file fully styled with merged break blocks and thick borders.
- **Comprehensive CRUD Management**: Easily manage Departments, Classes, Subjects, Faculties, and Rooms through a beautiful graphical interface.
- **Modern UI Edge**: Built thoroughly with Tailwind CSS, offering clean gradients, minimalist modal forms, floating labels, and active navigation states.
- **Role & Foreign-Key Safety**: Integrated dependency checks that gracefully prevent administrators from accidentally deleting faculty members or rooms that are actively assigned to generated schedules.

## 🛠️ Tech Stack

- **Backend**: Python, Flask, Flask-SQLAlchemy, Flask-Login
- **Frontend**: HTML5, Jinja2, Tailwind CSS, FontAwesome
- **Database**: SQLite (built-in)
- **Export Capabilities**: `openpyxl` (Excel), Native Browser `@media print` CSS

## ⚙️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone <your-repo-link>
   cd "Time table generator\timetable-generator"
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the Database & Sample Data:**
   First, run the application:
   ```bash
   python app.py
   ```
   Then navigate to your browser to map the first data set and database initialization (it will automatically build `timetable.db`):
   ```
   http://127.0.0.1:5000/init-sample-data
   ```

5. **Login:**
   Login via the main page (`http://127.0.0.1:5000`) using the generated admin credentials:
   - **username:** `admin`
   - **Password:** `admin123`

## 📘 How to Use

1. **Setup Data:** Navigate to the specific tabs (Departments, Classes, Subjects, Faculty, Rooms) to insert your organizational data.
2. **Assign Syllabi:** Use the **Class Subjects** mapper to attach specific theory and practical subjects to specific class batches.
3. **Generate:** Head to **Generate Timetable**, select your class, and watch the Genetic Algorithm resolve the constraints automatically!
4. **Export & Print:** Go to **View Timetable**, review the generated schedule, and hit **Print Timetable** (creates the perfect localized PDF) or **Export to Excel**.

## 🤝 Contribution & Maintenance
When iterating upon the `timetable.html` print logic, ensure that Tailwind's print utilities (`@media print`) and the CSS `zoom` constraints are respected, to prevent overflow onto a second printed sheet. Ensure Excel styles mapped in `app.py/export_timetable` accurately reflect any front-end additions.
