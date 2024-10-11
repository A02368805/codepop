# Setup Instructions for CodePop

Follow these instructions to set up the CodePop project on your machine.

## Backend Setup

1. **Install Dependencies**
   - Navigate to the base directory of your project and run the following command:
     ```bash
     pip install -r requirements.txt
     ```

2. **Download and Install PostgreSQL**
   - Download PostgreSQL from the following link:
     [PostgreSQL Downloads](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)

   - Refer to the installation guide for PostgreSQL:
     [PostgreSQL Installation Guide](https://www.enterprisedb.com/docs/supported-open-source/postgresql/installing/windows/)

   - **Important:** When installing PostgreSQL, use the following credentials (this will make it easier to pull from the repository):
     - **Username:** `postgres`
     - **Password:** `password`

3. **Sign in to PostgreSQL**
   - After installation, sign in to PostgreSQL as your user by running:
     ```bash
     psql -U postgres
     ```

4. **Create the Database**
   - The first time you run the app, you will need to create the database using the following command (do not change the database name):
     ```sql
     CREATE DATABASE codepop_database;
     ```

5. **Run Migrations and Start the Server**
   - Run the following commands to apply migrations and start the server:
     ```bash
     python manage.py migrate
     python manage.py runserver <YOUR IP ADDRESS:8000>
     ```
   - **Note:** Each time you run the server, you will need to provide your IP address. This is necessary for the Android emulator to access the backend. you can find your ip address by using the ipconfig command in the terminal

## Frontend Setup

1. **Install Node.js**
   - Download and install Node.js from the official website:
     [Node.js Downloads](https://nodejs.org/en)

2. **Install Android Studio**
   - Download and install Android Studio, then set up a virtual Android device:
     [Android Studio Downloads](https://developer.android.com/studio)

3. **Start the React Native App**
   - Navigate to the `codepop` directory and edit the base URL in `app.js` to match your IP address and port.
   - Run the following command to start the app:
     ```bash
     npm run android
     ```

You should now see a terminal displaying logs from the backend and an Android emulator with the app running!

## Troubleshooting
If you encounter any issues while setting up or running the application, feel free to reach out for help!
