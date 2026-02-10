# CodePop Web App - Quick Start Guide

## What Changed

The React Native frontend has been **replaced** with a Django + HTMX fullstack web application.

### Key Changes:
1. **Frontend Nuked**: Old React Native code in `codepop/` is now ignored
2. **Django Templates**: New HTML templates with HTMX for dynamic interactions
3. **Simplified Stack**: Just Django + HTMX + Tailwind CSS (via CDN)
4. **AI Features Disabled**: ML-heavy features temporarily commented out (no scipy/torch needed)

## Running the Application

### 1. Activate Virtual Environment
```bash
cd /home/curt/Code/codepop
source codepop_virtual_environment/bin/activate
```

### 2. Start the Server
```bash
cd codepop_backend
python manage.py runserver
```

### 3. Access the App
Open your browser to: **http://127.0.0.1:8000/**

## Features Available

### 1. **Drink Builder** (Feature #1 from brainstorm)
- Navigate to: http://127.0.0.1:8000/drinks/builder/
- **Live Price Calculator**: Price updates in real-time as you add ingredients (HTMX magic!)
- Select:
  - Drink name
  - Size (Small/Medium/Large)
  - Ice amount
  - Base soda
  - Multiple syrups
  - Multiple add-ins
- **Dynamic pricing**:
  - Small: $2.50, Medium: $3.50, Large: $4.50
  - +$0.50 per syrup
  - +$0.75 per add-in

### 2. **Drink Menu/List**
- Navigate to: http://127.0.0.1:8000/drinks/
- View all drinks in a table
- Delete drinks with HTMX (smooth fade-out animation)
- See all drink details and prices

### 3. **Home Page**
- Navigate to: http://127.0.0.1:8000/
- Landing page with links to main features

## Test Data

The database has been populated with test data:

### Users
- **Username**: `test`, **Password**: `password`
- **Username**: `test2`, **Password**: `password`
- **Username**: `super`, **Password**: `password` (superuser)
- **Username**: `staff`, **Password**: `password` (staff/manager)

### Inventory
The inventory is populated with:
- **Sodas**: Coke, Dr. Pepper, Sprite, Root Beer, Lemonade, etc.
- **Syrups**: Vanilla, Cherry, Chocolate, Caramel, Pumpkin Spice, etc.
- **Add-Ins**: Cream, Whipped Cream, Cherry, Candy Sprinkles, etc.

### Preset Drinks
Several preset drinks are available:
- Coke Float
- Seasonal Depression
- Fall Girlie
- Red Rizz
- #Lemons

## Tech Stack

- **Backend**: Django 6.0.2
- **Frontend**: Django Templates + HTMX 1.9.10
- **Styling**: Tailwind CSS (CDN)
- **Database**: PostgreSQL
- **Interactive Elements**: HTMX for dynamic updates without page reloads

## File Structure

```
codepop_backend/
├── templates/
│   ├── base.html           # Base template with HTMX
│   ├── home.html           # Landing page
│   ├── drink_builder.html  # Drink creation form
│   ├── drink_list.html     # Drink menu table
│   └── login.html          # Login page
├── static/
│   ├── css/
│   │   └── style.css       # Custom CSS
│   └── js/                 # (empty for now)
├── backend/
│   ├── web_views.py        # New template-based views
│   └── web_urls.py         # Web interface URLs
└── codepop_backend/
    ├── settings.py         # Updated with templates/static config
    └── urls.py             # Includes web_urls at root

API Endpoints (still available):
- /api/* - Original REST API endpoints
```

## What's Next?

For the show and tell demo, you can showcase:

1. **Live Price Calculator**:
   - Open drink builder
   - Start adding ingredients
   - Watch price update in real-time without page refresh

2. **Smooth Interactions**:
   - Delete drinks with fade-out animation
   - No page reloads thanks to HTMX

3. **Clean UI**:
   - Professional gradient design (purple to pink)
   - Responsive layout
   - Easy to navigate

## Reset Database (if needed)

```bash
cd codepop_backend
./clean_database.sh
```

This will clear all data and repopulate with test data.

## Notes

- **Old React Native frontend** is now in `.gitignore`
- **AI features** are temporarily disabled (would need scipy, torch, transformers)
- **API endpoints** still work at `/api/*` if needed
- **Simple CRUD** focus for prototype
