Markdown
# ArcangeleSite Premium | Student Directory v2.0
**A Sophisticated Student Management System for BSIT 2A**

ArcangeleSite is a high-end, responsive student directory built with Django. It bridges the gap between administrative utility and a "Quiet Luxury" design aesthetic, featuring Glassmorphism UI elements, real-time search functionality, and a secure data management architecture.

## ✨ Key Features

* **Live Search & Auto-Load:** Integrated JavaScript-driven search with a 1.2s debounce timer for a seamless, "app-like" experience without manual refreshing.
* **Premium Glassmorphism UI:** A custom frontend utilizing backdrop filters, high-contrast dark themes, and the Plus Jakarta Sans typeface for a modern look.
* **Soft Delete & Archiving:** Implements a logical deletion system (is_active flag), ensuring student data remains retrievable even after removal from the primary directory.
* **Smart Media Management:** Robust profile picture handling with `enctype="multipart/form-data"` support and minimalist "N/A" placeholders for records without media.
* **Relational Database Integrity:** Normalized database structure (3NF) managing Student-Gender relationships via Django Foreign Keys.
* **Administrative Export:** One-click CSV generation for fast data reporting and portability.

## 🛠️ Tech Stack

* **Backend:** Python 3.x, Django 5.x
* **Frontend:** HTML5, CSS3 (Glassmorphism), JavaScript (ES6+), Bootstrap 5
* **Icons & Fonts:** Bootstrap Icons, Google Fonts (Plus Jakarta Sans)
* **Storage:** Django Media Framework (Profile Pictures)

## 🚀 Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Dodzminic/arcangelessite.git](https://github.com/Dodzminic/arcangelessite.git)
Install requirements:

Bash
pip install django pillow
Database Setup:

Bash
python manage.py makemigrations
python manage.py migrate
Launch Application:

Bash
python manage.py runserver
📐 Project Folder Structure
crud/: Core application logic, views, and forms.

media/: Managed storage for student profile uploads.

templates/: Premium UI components and directory layout.

Developed by Desriel Dominic Arcangeles BSIT Student @ Filamer Christian University | Graphic Designer | IT Enthusiast