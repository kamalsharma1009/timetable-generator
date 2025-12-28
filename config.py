import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_PERMANENT = False
    SESSION_TYPE = 'filesystem'
    
    # Timetable settings
    DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    TIME_SLOTS = [
        ('09:40', '10:40'),
        ('10:50', '11:50'),
        ('11:50', '12:40'),  # Lunch break
        ('12:40', '13:40'),
        ('13:50', '14:50'),
        ('15:00', '16:00'),
        ('16:10', '17:10')
    ]
    LECTURE_SLOT_INDICES = [0, 1, 3, 4, 5, 6]  # Indices excluding lunch break
    PRACTICAL_SLOTS = [('14:00', '16:00'), ('15:00', '17:10')]
    
    # Genetic Algorithm parameters
    POPULATION_SIZE = 100
    GENERATIONS = 500
    MUTATION_RATE = 0.1
    ELITE_SIZE = 20