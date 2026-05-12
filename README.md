Markdown
# ArcangeleSite Premium | Student Directory v2.0
**A Sophisticated Student Management System for BSIT 2A**

ArcangeleSite is a high-end, responsive student directory built with Django. It combines technical efficiency with a "Quiet Luxury" and "Sophisticated Minimalist" design aesthetic, featuring Glassmorphism UI elements and real-time data processing.

## ✨ Key Features

* **Live Search & Filter:** Real-time search functionality with a custom-tuned 1.2s delay for a seamless user experience.
* **Premium Glassmorphism UI:** Built with Tailwind CSS and Bootstrap, utilizing backdrop filters and high-contrast dark themes.
* **Soft Delete System:** An archive-first approach to data management, ensuring student records are never accidentally lost.
* **Dynamic Image Handling:** Smart profile picture uploads with a custom "N/A" minimalist placeholder for missing media.
* **Data Portability:** Integrated CSV export functionality for administrative reporting.
* **Bulk Actions:** Efficient multi-select archiving system for database management.

## 🛠️ Tech Stack

* **Backend:** Python 3.x, Django 5.x
* **Frontend:** HTML5, CSS3 (Glassmorphism), JavaScript (ES6+), Bootstrap 5
* **Database:** MS Access / MySQL (Normalized to 3NF)
* **Design:** Plus Jakarta Sans Typography, Bi-Icon Library

## 🚀 Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/yourusername/arcangelesite.git](https://github.com/yourusername/arcangelesite.git)
Install dependencies:

Bash
pip install django pillow
Apply migrations:

Bash
python manage.py makemigrations
python manage.py migrate
Run the development server:

Bash
python manage.py runserver
📐 Project Structure
crud/: Main application logic.

media/: Managed student profile uploads.

static/: High-end CSS and UI assets.

Developed by Desriel Dominic Arcangeles Second Year BSIT Student | Graphic Designer | IT Enthusiast