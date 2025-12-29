from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, time
import json
import os
import random
import copy
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-key-12345'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Timetable settings
app.config['DAYS'] = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
app.config['TIME_SLOTS'] = [
    ('09:40', '10:40'),
    ('10:50', '11:50'),
    ('11:50', '12:40'),  # Lunch break
    ('12:40', '13:40'),
    ('13:50', '14:50'),
    ('15:00', '16:00'),
    ('16:10', '17:10')
]
app.config['LECTURE_SLOT_INDICES'] = [0, 1, 3, 4, 5, 6]
app.config['PRACTICAL_SLOTS'] = [('14:00', '16:00'), ('15:00', '17:10')]

# Genetic Algorithm parameters
app.config['POPULATION_SIZE'] = 100
app.config['GENERATIONS'] = 500
app.config['MUTATION_RATE'] = 0.1
app.config['ELITE_SIZE'] = 20

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models (defined here to avoid circular imports)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    classes = db.relationship('Class', backref='department', lazy=True)
    faculty = db.relationship('Faculty', backref='department', lazy=True)

class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    year = db.Column(db.String(10), nullable=False)  # FY, SY, TY
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    strength = db.Column(db.Integer, default=60)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    subjects = db.relationship('ClassSubject', backref='class_ref', lazy=True)
    batches = db.relationship('Batch', backref='class_ref', lazy=True)
    timetable = db.relationship('Timetable', backref='class_ref', lazy=True)

class Batch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(10), nullable=False)  # TB1, TB2, TB3
    code = db.Column(db.String(30), unique=True, nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    mentor_id = db.Column(db.Integer, db.ForeignKey('faculty.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    practical_slots = db.relationship('PracticalSlot', backref='batch', lazy=True)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # Theory, Practical, Lab, Tutorial
    lecture_hours = db.Column(db.Integer, default=0)
    practical_hours = db.Column(db.Integer, default=0)
    credits = db.Column(db.Integer, default=3)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    class_subjects = db.relationship('ClassSubject', backref='subject_ref', lazy=True)

class ClassSubject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'))
    lecture_slots_per_week = db.Column(db.Integer, default=3)
    practical_slots_per_week = db.Column(db.Integer, default=2)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Faculty(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(15))
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    designation = db.Column(db.String(50))
    qualification = db.Column(db.String(100))
    max_hours_per_day = db.Column(db.Integer, default=4)
    max_hours_per_week = db.Column(db.Integer, default=20)
    availability = db.Column(db.Text, default='{}')  # JSON storing availability per day
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    class_subjects = db.relationship('ClassSubject', backref='faculty_ref', lazy=True)
    mentored_batches = db.relationship('Batch', backref='mentor', lazy=True)
    timetable_entries = db.relationship('Timetable', backref='faculty_ref', lazy=True)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(20), unique=True, nullable=False)
    room_type = db.Column(db.String(20), nullable=False)  # Classroom, Lab, Auditorium
    capacity = db.Column(db.Integer, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    equipment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    timetable_entries = db.relationship('Timetable', backref='room', lazy=True)

class Timetable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    day = db.Column(db.String(10), nullable=False)
    slot_number = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'))
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'))
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'))
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'))
    session_type = db.Column(db.String(20), nullable=False)  # Lecture, Practical, Mentoring, Break
    is_break = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PracticalSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'))
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'))
    day = db.Column(db.String(10), nullable=False)
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Create tables before first request
with app.app_context():
    db.create_all()
    # Create default admin user if not exists
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@college.edu', is_admin=True)
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Default admin user created: username='admin', password='admin123'")

# Genetic Algorithm Class (moved here to avoid circular imports)
class GeneticAlgorithmTimetable:
    def __init__(self, class_id):
        self.class_id = class_id
        self.class_obj = Class.query.get(class_id)
        self.days = app.config['DAYS']
        self.time_slots = [
            (0, '09:40', '10:40', False),   # Slot 1
            (1, '10:50', '11:50', False),   # Slot 2
            (2, '11:50', '12:40', True),    # Lunch break
            (3, '12:40', '13:40', False),   # Slot 3
            (4, '13:50', '14:50', False),   # Slot 4
            (5, '15:00', '16:00', False),   # Slot 5
            (6, '16:10', '17:10', False)    # Slot 6
        ]
        self.lecture_slots = app.config['LECTURE_SLOT_INDICES']
        
        # Get all required data
        self.class_subjects = ClassSubject.query.filter_by(class_id=class_id).all()
        self.batches = Batch.query.filter_by(class_id=class_id).all()
        self.faculty_list = Faculty.query.all()
        self.rooms = Room.query.all()
        self.classrooms = [r for r in self.rooms if r.room_type == 'Classroom']
        self.labs = [r for r in self.rooms if r.room_type == 'Lab']
        
        if not self.classrooms:
            self.classrooms = [Room(room_number='Default Classroom', room_type='Classroom', capacity=60)]
        if not self.labs:
            self.labs = [Room(room_number='Default Lab', room_type='Lab', capacity=40)]
        
        # Initialize population
        self.population = []
        self.best_solution = None
        self.best_fitness = float('-inf')
        
    def create_individual(self):
        """Create one feasible timetable individual"""
        individual = {
            'lectures': [],
            'practicals': [],
            'mentoring': []
        }
        
        # Try to create a feasible individual
        max_attempts = 50
        for attempt in range(max_attempts):
            try:
                # 1. Schedule lectures
                for class_subject in self.class_subjects:
                    lecture_count = class_subject.lecture_slots_per_week
                    scheduled = 0
                    
                    while scheduled < lecture_count:
                        day = random.choice(self.days)
                        slot_idx = random.choice(self.lecture_slots)
                        
                        # Skip lunch break
                        if slot_idx == 2:
                            continue
                            
                        # Check faculty availability
                        faculty_busy = self.check_faculty_busy(individual, class_subject.faculty_id, day, slot_idx)
                        if faculty_busy:
                            continue
                        
                        # Find available classroom
                        classroom = self.find_available_classroom(individual, day, slot_idx)
                        if not classroom:
                            continue
                        
                        slot = self.time_slots[slot_idx]
                        individual['lectures'].append({
                            'class_subject_id': class_subject.id,
                            'subject_id': class_subject.subject_id,
                            'faculty_id': class_subject.faculty_id,
                            'room_id': classroom.id,
                            'day': day,
                            'slot_number': slot_idx,
                            'start_time': slot[1],
                            'end_time': slot[2],
                            'session_type': 'Lecture'
                        })
                        scheduled += 1
                
                # 2. Schedule practicals for each batch
                for batch in self.batches:
                    for class_subject in self.class_subjects:
                        practical_count = class_subject.practical_slots_per_week
                        scheduled = 0
                        
                        while scheduled < practical_count:
                            # Schedule 2-hour practical in afternoon
                            day = random.choice(self.days)
                            # Use slots 4-5 or 5-6 for practicals (afternoon)
                            start_slot = random.choice([4, 5])
                            end_slot = start_slot + 1
                            
                            if end_slot > 6:  # Ensure within bounds
                                continue
                            
                            # Check faculty availability for both slots
                            faculty_busy = False
                            for slot in [start_slot, end_slot]:
                                if self.check_faculty_busy(individual, class_subject.faculty_id, day, slot):
                                    faculty_busy = True
                                    break
                            
                            if faculty_busy:
                                continue
                            
                            # Find available lab
                            lab = self.find_available_lab(individual, day, start_slot, end_slot)
                            if not lab:
                                continue
                            
                            individual['practicals'].append({
                                'batch_id': batch.id,
                                'subject_id': class_subject.subject_id,
                                'faculty_id': class_subject.faculty_id,
                                'room_id': lab.id,
                                'day': day,
                                'start_slot': start_slot,
                                'end_slot': end_slot,
                                'start_time': self.time_slots[start_slot][1],
                                'end_time': self.time_slots[end_slot][2],
                                'session_type': 'Practical'
                            })
                            scheduled += 1
                
                # 3. Schedule mentoring sessions
                for batch in self.batches:
                    if batch.mentor_id:
                        for _ in range(20):  # Try 20 times
                            day = random.choice(self.days)
                            slot_idx = random.choice(self.lecture_slots)
                            
                            # Skip lunch break
                            if slot_idx == 2:
                                continue
                                
                            # Check mentor availability
                            if self.check_faculty_busy(individual, batch.mentor_id, day, slot_idx):
                                continue
                            
                            classroom = self.find_available_classroom(individual, day, slot_idx)
                            if not classroom:
                                continue
                            
                            slot = self.time_slots[slot_idx]
                            individual['mentoring'].append({
                                'batch_id': batch.id,
                                'faculty_id': batch.mentor_id,
                                'room_id': classroom.id,
                                'day': day,
                                'slot_number': slot_idx,
                                'start_time': slot[1],
                                'end_time': slot[2],
                                'session_type': 'Mentoring'
                            })
                            break
                
                return individual
                
            except Exception as e:
                # Reset and try again
                individual = {'lectures': [], 'practicals': [], 'mentoring': []}
                continue
        
        # If we couldn't create a feasible individual after max attempts, return what we have
        return individual
    
    def check_faculty_busy(self, individual, faculty_id, day, slot_number):
        """Check if faculty is already busy at given day and slot"""
        if not faculty_id:
            return False
            
        # Check lectures
        for lecture in individual['lectures']:
            if (lecture['faculty_id'] == faculty_id and 
                lecture['day'] == day and 
                lecture['slot_number'] == slot_number):
                return True
        
        # Check practicals
        for practical in individual['practicals']:
            if practical['faculty_id'] == faculty_id and practical['day'] == day:
                if slot_number >= practical['start_slot'] and slot_number <= practical['end_slot']:
                    return True
        
        # Check mentoring
        for mentoring in individual['mentoring']:
            if (mentoring['faculty_id'] == faculty_id and 
                mentoring['day'] == day and 
                mentoring['slot_number'] == slot_number):
                return True
        
        return False
    
    def find_available_classroom(self, individual, day, slot_number):
        """Find available classroom for given time slot"""
        if not self.classrooms:
            return None
            
        available_classrooms = self.classrooms.copy()
        
        # Remove classrooms that are occupied
        for lecture in individual['lectures']:
            if lecture['day'] == day and lecture['slot_number'] == slot_number:
                available_classrooms = [r for r in available_classrooms if r.id != lecture['room_id']]
        
        for mentoring in individual['mentoring']:
            if mentoring['day'] == day and mentoring['slot_number'] == slot_number:
                available_classrooms = [r for r in available_classrooms if r.id != mentoring['room_id']]
        
        return random.choice(available_classrooms) if available_classrooms else None
    
    def find_available_lab(self, individual, day, start_slot, end_slot):
        """Find available lab for 2-hour practical"""
        if not self.labs:
            return None
            
        available_labs = self.labs.copy()
        
        # Remove labs that are occupied during these slots
        for practical in individual['practicals']:
            if practical['day'] == day:
                # Check for overlap
                if not (end_slot < practical['start_slot'] or start_slot > practical['end_slot']):
                    available_labs = [r for r in available_labs if r.id != practical['room_id']]
        
        return random.choice(available_labs) if available_labs else None
    
    def calculate_fitness(self, individual):
        """Calculate fitness score for individual"""
        fitness = 1000  # Base score
        
        # Penalties for violations
        penalties = 0
        
        # 1. Check faculty overload
        faculty_hours = {}
        for lecture in individual['lectures']:
            fid = lecture['faculty_id']
            if fid:
                faculty_hours[fid] = faculty_hours.get(fid, 0) + 1
        
        for practical in individual['practicals']:
            fid = practical['faculty_id']
            if fid:
                faculty_hours[fid] = faculty_hours.get(fid, 0) + 2
        
        for mentoring in individual['mentoring']:
            fid = mentoring['faculty_id']
            if fid:
                faculty_hours[fid] = faculty_hours.get(fid, 0) + 1
        
        # Check against faculty max hours (simplified)
        for fid, hours in faculty_hours.items():
            if hours > 20:  # Default max hours
                penalties += (hours - 20) * 10
        
        # 2. Check room conflicts
        room_schedule = {}
        for lecture in individual['lectures']:
            key = (lecture['room_id'], lecture['day'], lecture['slot_number'])
            if key in room_schedule:
                penalties += 50
            room_schedule[key] = True
        
        # 3. Check if all subjects have required hours (simplified)
        subject_lecture_hours = {}
        subject_practical_hours = {}
        
        for lecture in individual['lectures']:
            sid = lecture['subject_id']
            subject_lecture_hours[sid] = subject_lecture_hours.get(sid, 0) + 1
        
        for practical in individual['practicals']:
            sid = practical['subject_id']
            subject_practical_hours[sid] = subject_practical_hours.get(sid, 0) + 2
        
        for class_subject in self.class_subjects:
            required_lecture = class_subject.lecture_slots_per_week
            required_practical = class_subject.practical_slots_per_week * 2  # 2 hours each
            
            actual_lecture = subject_lecture_hours.get(class_subject.subject_id, 0)
            actual_practical = subject_practical_hours.get(class_subject.subject_id, 0)
            
            if actual_lecture < required_lecture:
                penalties += (required_lecture - actual_lecture) * 30
            if actual_practical < required_practical:
                penalties += (required_practical - actual_practical) * 40
        
        # 4. Reward for having all batches with mentoring
        mentoring_count = len(individual['mentoring'])
        required_mentoring = len([b for b in self.batches if b.mentor_id])
        if mentoring_count < required_mentoring:
            penalties += (required_mentoring - mentoring_count) * 100
        
        fitness -= penalties
        return max(fitness, 0)  # Ensure fitness is not negative
    
    def crossover(self, parent1, parent2):
        """Create child through crossover"""
        child = {
            'lectures': [],
            'practicals': [],
            'mentoring': []
        }
        
        # Simple crossover: take half from each parent
        if parent1['lectures'] and parent2['lectures']:
            split = len(parent1['lectures']) // 2
            child['lectures'] = parent1['lectures'][:split] + parent2['lectures'][split:]
        
        if parent1['practicals'] and parent2['practicals']:
            split = len(parent1['practicals']) // 2
            child['practicals'] = parent1['practicals'][:split] + parent2['practicals'][split:]
        
        if parent1['mentoring'] and parent2['mentoring']:
            split = len(parent1['mentoring']) // 2
            child['mentoring'] = parent1['mentoring'][:split] + parent2['mentoring'][split:]
        
        return child
    
    def mutate(self, individual):
        """Apply mutation to individual"""
        if individual['lectures'] and random.random() < 0.3:
            # Mutate a random lecture
            idx = random.randint(0, len(individual['lectures']) - 1)
            lecture = individual['lectures'][idx]
            
            # Change day or slot
            if random.random() < 0.5:
                lecture['day'] = random.choice(self.days)
            else:
                new_slot = random.choice([s for s in self.lecture_slots if s != 2])  # Skip lunch
                lecture['slot_number'] = new_slot
                slot = self.time_slots[new_slot]
                lecture['start_time'] = slot[1]
                lecture['end_time'] = slot[2]
        
        return individual
    
    def evolve(self, population_size=30, generations=50, mutation_rate=0.2, elite_size=5):
        """Run genetic algorithm evolution"""
        print(f"Starting GA evolution for class {self.class_obj.name}")
        
        # Initialize population
        self.population = []
        for i in range(population_size):
            print(f"Creating individual {i+1}/{population_size}")
            individual = self.create_individual()
            self.population.append(individual)
        
        for generation in range(generations):
            # Calculate fitness for each individual
            fitness_scores = []
            for individual in self.population:
                fitness = self.calculate_fitness(individual)
                fitness_scores.append((fitness, individual))
            
            # Sort by fitness
            fitness_scores.sort(key=lambda x: x[0], reverse=True)
            
            # Update best solution
            if fitness_scores[0][0] > self.best_fitness:
                self.best_fitness = fitness_scores[0][0]
                self.best_solution = copy.deepcopy(fitness_scores[0][1])
                print(f"Generation {generation}: New best fitness = {self.best_fitness}")
            
            # Select elite
            elites = [ind for _, ind in fitness_scores[:elite_size]]
            
            # Create next generation
            next_generation = elites.copy()
            
            # Generate offspring
            while len(next_generation) < population_size:
                # Tournament selection
                if len(fitness_scores) > 10:
                    parent1 = random.choice(fitness_scores[:10])[1]
                    parent2 = random.choice(fitness_scores[:10])[1]
                else:
                    parent1 = fitness_scores[0][1] if fitness_scores else self.create_individual()
                    parent2 = fitness_scores[1][1] if len(fitness_scores) > 1 else self.create_individual()
                
                child = self.crossover(parent1, parent2)
                
                # Apply mutation
                if random.random() < mutation_rate:
                    child = self.mutate(child)
                
                next_generation.append(child)
            
            self.population = next_generation
        
        print(f"GA completed. Best fitness: {self.best_fitness}")
        return self.best_solution
    
    def save_to_database(self, solution):
        """Save generated timetable to database"""
        # Clear existing timetable for this class
        Timetable.query.filter_by(class_id=self.class_id).delete()
        PracticalSlot.query.filter_by(class_id=self.class_id).delete()
        db.session.commit()
        
        # Save lectures
        for lecture in solution['lectures']:
            timetable_entry = Timetable(
                class_id=self.class_id,
                day=lecture['day'],
                slot_number=lecture['slot_number'],
                start_time=lecture['start_time'],
                end_time=lecture['end_time'],
                subject_id=lecture['subject_id'],
                faculty_id=lecture['faculty_id'],
                room_id=lecture['room_id'],
                session_type='Lecture',
                is_break=False
            )
            db.session.add(timetable_entry)
        
        # Save practicals
        for practical in solution['practicals']:
            practical_slot = PracticalSlot(
                class_id=self.class_id,
                batch_id=practical['batch_id'],
                subject_id=practical['subject_id'],
                faculty_id=practical['faculty_id'],
                room_id=practical['room_id'],
                day=practical['day'],
                start_time=practical['start_time'],
                end_time=practical['end_time']
            )
            db.session.add(practical_slot)
            
            # Also add to timetable
            timetable_entry = Timetable(
                class_id=self.class_id,
                day=practical['day'],
                slot_number=practical['start_slot'],
                start_time=practical['start_time'],
                end_time=practical['end_time'],
                subject_id=practical['subject_id'],
                faculty_id=practical['faculty_id'],
                room_id=practical['room_id'],
                batch_id=practical['batch_id'],
                session_type='Practical',
                is_break=False
            )
            db.session.add(timetable_entry)
        
        # Save mentoring
        for mentoring in solution['mentoring']:
            timetable_entry = Timetable(
                class_id=self.class_id,
                day=menturing['day'],
                slot_number=menturing['slot_number'],
                start_time=menturing['start_time'],
                end_time=menturing['end_time'],
                faculty_id=menturing['faculty_id'],
                room_id=menturing['room_id'],
                batch_id=menturing['batch_id'],
                session_type='Mentoring',
                is_break=False
            )
            db.session.add(timetable_entry)
        
        # Add break slots
        for day in self.days:
            # Lunch break
            lunch_break = Timetable(
                class_id=self.class_id,
                day=day,
                slot_number=2,
                start_time='11:50',
                end_time='12:40',
                session_type='Break',
                is_break=True
            )
            db.session.add(lunch_break)
        
        db.session.commit()
        print(f"Timetable saved to database for class {self.class_id}")
        return True

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email, is_admin=True)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get statistics
    dept_count = Department.query.count()
    class_count = Class.query.count()
    faculty_count = Faculty.query.count()
    subject_count = Subject.query.count()
    
    # Get recent activity
    recent_classes = Class.query.order_by(Class.created_at.desc()).limit(5).all()
    
    return render_template('dashboard.html',
                         dept_count=dept_count,
                         class_count=class_count,
                         faculty_count=faculty_count,
                         subject_count=subject_count,
                         recent_classes=recent_classes)

# Department Management
@app.route('/departments')
@login_required
def manage_departments():
    departments = Department.query.all()
    return render_template('departments.html', departments=departments)

@app.route('/departments/add', methods=['POST'])
@login_required
def add_department():
    code = request.form.get('code')
    name = request.form.get('name')
    description = request.form.get('description')
    
    if Department.query.filter_by(code=code).first():
        flash('Department code already exists', 'error')
        return redirect(url_for('manage_departments'))
    
    department = Department(code=code, name=name, description=description)
    db.session.add(department)
    db.session.commit()
    
    flash('Department added successfully', 'success')
    return redirect(url_for('manage_departments'))

@app.route('/departments/delete/<int:id>')
@login_required
def delete_department(id):
    department = Department.query.get_or_404(id)
    db.session.delete(department)
    db.session.commit()
    flash('Department deleted successfully', 'success')
    return redirect(url_for('manage_departments'))

# Class Management
@app.route('/classes')
@login_required
def manage_classes():
    classes = Class.query.all()
    departments = Department.query.all()
    semesters = list(range(1, 7))
    return render_template('classes.html', classes=classes, departments=departments, semesters=semesters)

@app.route('/classes/add', methods=['POST'])
@login_required
def add_class():
    name = request.form.get('name')
    code = request.form.get('code')
    year = request.form.get('year')
    department_id = request.form.get('department_id')
    semester = request.form.get('semester')
    strength = request.form.get('strength', 60)
    
    if Class.query.filter_by(code=code).first():
        flash('Class code already exists', 'error')
        return redirect(url_for('manage_classes'))
    
    class_obj = Class(
        name=name,
        code=code,
        year=year,
        department_id=department_id,
        semester=semester,
        strength=strength
    )
    
    db.session.add(class_obj)
    db.session.flush()  # Get the ID
    
    # Create batches (TB1, TB2, TB3)
    for i in range(1, 4):
        batch = Batch(
            name=f'TB{i}',
            code=f'{code}_TB{i}',
            class_id=class_obj.id
        )
        db.session.add(batch)
    
    db.session.commit()
    
    flash('Class and batches created successfully', 'success')
    return redirect(url_for('manage_classes'))

# Subject Management
@app.route('/subjects')
@login_required
def manage_subjects():
    subjects = Subject.query.all()
    departments = Department.query.all()
    return render_template('subjects.html', subjects=subjects, departments=departments)

@app.route('/subjects/add', methods=['POST'])
@login_required
def add_subject():
    code = request.form.get('code')
    name = request.form.get('name')
    type = request.form.get('type')
    lecture_hours = request.form.get('lecture_hours', 0, type=int)
    practical_hours = request.form.get('practical_hours', 0, type=int)
    credits = request.form.get('credits', 3, type=int)
    department_id = request.form.get('department_id')
    
    if Subject.query.filter_by(code=code).first():
        flash('Subject code already exists', 'error')
        return redirect(url_for('manage_subjects'))
    
    subject = Subject(
        code=code,
        name=name,
        type=type,
        lecture_hours=lecture_hours,
        practical_hours=practical_hours,
        credits=credits,
        department_id=department_id if department_id else None
    )
    
    db.session.add(subject)
    db.session.commit()
    
    flash('Subject added successfully', 'success')
    return redirect(url_for('manage_subjects'))

# Faculty Management
@app.route('/faculty')
@login_required
def manage_faculty():
    faculty_list = Faculty.query.all()
    departments = Department.query.all()
    return render_template('faculty.html', faculty_list=faculty_list, departments=departments)

@app.route('/faculty/add', methods=['POST'])
@login_required
def add_faculty():
    employee_id = request.form.get('employee_id')
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    department_id = request.form.get('department_id')
    designation = request.form.get('designation')
    qualification = request.form.get('qualification')
    
    if Faculty.query.filter_by(employee_id=employee_id).first():
        flash('Employee ID already exists', 'error')
        return redirect(url_for('manage_faculty'))
    
    if Faculty.query.filter_by(email=email).first():
        flash('Email already exists', 'error')
        return redirect(url_for('manage_faculty'))
    
    faculty = Faculty(
        employee_id=employee_id,
        name=name,
        email=email,
        phone=phone,
        department_id=department_id if department_id else None,
        designation=designation,
        qualification=qualification
    )
    
    db.session.add(faculty)
    db.session.commit()
    
    flash('Faculty added successfully', 'success')
    return redirect(url_for('manage_faculty'))

# Room Management
@app.route('/rooms')
@login_required
def manage_rooms():
    rooms = Room.query.all()
    departments = Department.query.all()
    return render_template('rooms.html', rooms=rooms, departments=departments)

@app.route('/rooms/add', methods=['POST'])
@login_required
def add_room():
    room_number = request.form.get('room_number')
    room_type = request.form.get('room_type')
    capacity = request.form.get('capacity', type=int)
    department_id = request.form.get('department_id')
    equipment = request.form.get('equipment')
    
    if Room.query.filter_by(room_number=room_number).first():
        flash('Room number already exists', 'error')
        return redirect(url_for('manage_rooms'))
    
    room = Room(
        room_number=room_number,
        room_type=room_type,
        capacity=capacity,
        department_id=department_id if department_id else None,
        equipment=equipment
    )
    
    db.session.add(room)
    db.session.commit()
    
    flash('Room added successfully', 'success')
    return redirect(url_for('manage_rooms'))

# Class Subjects Assignment
@app.route('/class-subjects/<int:class_id>')
@login_required
def manage_class_subjects(class_id):
    class_obj = Class.query.get_or_404(class_id)
    subjects = Subject.query.all()
    faculty_list = Faculty.query.all()
    class_subjects = ClassSubject.query.filter_by(class_id=class_id).all()
    
    return render_template('class_subjects.html',
                         class_obj=class_obj,
                         subjects=subjects,
                         faculty_list=faculty_list,
                         class_subjects=class_subjects)

@app.route('/class-subjects/add', methods=['POST'])
@login_required
def add_class_subject():
    class_id = request.form.get('class_id')
    subject_id = request.form.get('subject_id')
    faculty_id = request.form.get('faculty_id')
    lecture_slots = request.form.get('lecture_slots', 3, type=int)
    practical_slots = request.form.get('practical_slots', 2, type=int)
    
    # Check if already assigned
    existing = ClassSubject.query.filter_by(class_id=class_id, subject_id=subject_id).first()
    if existing:
        flash('Subject already assigned to this class', 'error')
        return redirect(url_for('manage_class_subjects', class_id=class_id))
    
    class_subject = ClassSubject(
        class_id=class_id,
        subject_id=subject_id,
        faculty_id=faculty_id,
        lecture_slots_per_week=lecture_slots,
        practical_slots_per_week=practical_slots
    )
    
    db.session.add(class_subject)
    db.session.commit()
    
    flash('Subject assigned successfully', 'success')
    return redirect(url_for('manage_class_subjects', class_id=class_id))

# Batch Mentors Assignment
@app.route('/batch-mentors/<int:class_id>')
@login_required
def manage_batch_mentors(class_id):
    class_obj = Class.query.get_or_404(class_id)
    batches = Batch.query.filter_by(class_id=class_id).all()
    faculty_list = Faculty.query.all()
    
    return render_template('batch_mentors.html',
                         class_obj=class_obj,
                         batches=batches,
                         faculty_list=faculty_list)

@app.route('/batch-mentors/assign', methods=['POST'])
@login_required
def assign_batch_mentor():
    batch_id = request.form.get('batch_id')
    mentor_id = request.form.get('mentor_id')
    
    batch = Batch.query.get_or_404(batch_id)
    batch.mentor_id = mentor_id
    
    db.session.commit()
    
    flash('Mentor assigned successfully', 'success')
    return redirect(url_for('manage_batch_mentors', class_id=batch.class_id))

# Generate Timetable
@app.route('/generate-timetable')
@login_required
def generate_timetable():
    classes = Class.query.all()
    return render_template('generate.html', classes=classes)

@app.route('/generate-timetable/run/<int:class_id>')
@login_required
def run_timetable_generation(class_id):
    try:
        # Check if class exists
        class_obj = Class.query.get_or_404(class_id)
        
        # Check if class has subjects assigned
        if not ClassSubject.query.filter_by(class_id=class_id).first():
            flash('Please assign subjects to this class first', 'error')
            return redirect(url_for('manage_class_subjects', class_id=class_id))
        
        # Check if rooms exist
        rooms = Room.query.all()
        if not rooms:
            flash('Please add classrooms and labs first', 'error')
            return redirect(url_for('manage_rooms'))
        
        # Initialize and run genetic algorithm
        ga = GeneticAlgorithmTimetable(class_id)
        solution = ga.evolve(population_size=20, generations=30)  # Reduced for speed
        
        if solution and ga.best_fitness > 0:
            ga.save_to_database(solution)
            flash('Timetable generated successfully!', 'success')
        else:
            flash('Failed to generate feasible timetable. Try adding more rooms or adjusting constraints.', 'error')
    
    except Exception as e:
        flash(f'Error generating timetable: {str(e)}', 'error')
        import traceback
        print(traceback.format_exc())
    
    return redirect(url_for('view_timetable', class_id=class_id))

# View Timetable
@app.route('/view-timetable')
@login_required
def view_timetable():
    class_id = request.args.get('class_id', type=int)
    classes = Class.query.all()
    
    timetable_data = None
    time_slots = app.config['TIME_SLOTS']
    
    if class_id:
        # Get timetable for selected class
        timetable_entries = Timetable.query.filter_by(class_id=class_id)\
            .order_by(Timetable.day, Timetable.slot_number).all()
        
        # Organize by day and slot
        timetable_data = {}
        days = app.config['DAYS']
        slots = list(range(7))
        
        for day in days:
            timetable_data[day] = {}
            for slot in slots:
                entries = [e for e in timetable_entries if e.day == day and e.slot_number == slot]
                timetable_data[day][slot] = entries
    
    return render_template('timetable.html',
                         classes=classes,
                         class_id=class_id,
                         timetable_data=timetable_data,
                         time_slots=time_slots)

# Initialize Sample Data
@app.route('/init-sample-data')
def init_sample_data():
    """Initialize with sample data for testing"""
    # Clear existing data
    db.session.query(Timetable).delete()
    db.session.query(PracticalSlot).delete()
    db.session.query(ClassSubject).delete()
    db.session.query(Batch).delete()
    db.session.query(Class).delete()
    db.session.query(Faculty).delete()
    db.session.query(Subject).delete()
    db.session.query(Room).delete()
    db.session.query(Department).delete()
    
    # Create departments
    dept1 = Department(code='CSE', name='Computer Engineering', description='Computer Science and Engineering Department')
    dept2 = Department(code='MECH', name='Mechanical Engineering', description='Mechanical Engineering Department')
    dept3 = Department(code='ENTC', name='Electronics & Telecommunication', description='ENTC Department')
    db.session.add_all([dept1, dept2, dept3])
    db.session.commit()
    
    # Create faculty
    faculty1 = Faculty(employee_id='F001', name='Dr. Rajesh Kumar', email='rajesh@college.edu', 
                      phone='9876543210', department_id=dept1.id, designation='Professor',
                      qualification='Ph.D. in Computer Science')
    faculty2 = Faculty(employee_id='F002', name='Prof. Sunita Sharma', email='sunita@college.edu',
                      phone='9876543211', department_id=dept1.id, designation='Associate Professor',
                      qualification='M.Tech in CSE')
    faculty3 = Faculty(employee_id='F003', name='Dr. Amit Patel', email='amit@college.edu',
                      phone='9876543212', department_id=dept2.id, designation='Professor',
                      qualification='Ph.D. in Mechanical Engineering')
    db.session.add_all([faculty1, faculty2, faculty3])
    db.session.commit()
    
    # Create rooms
    room1 = Room(room_number='A-101', room_type='Classroom', capacity=60, department_id=dept1.id)
    room2 = Room(room_number='A-102', room_type='Classroom', capacity=60, department_id=dept1.id)
    room3 = Room(room_number='LAB-1', room_type='Lab', capacity=40, department_id=dept1.id, 
                equipment='40 Computers, Projector')
    room4 = Room(room_number='B-201', room_type='Classroom', capacity=60, department_id=dept2.id)
    room5 = Room(room_number='LAB-2', room_type='Lab', capacity=30, department_id=dept2.id,
                equipment='CNC Machines, Lathes')
    db.session.add_all([room1, room2, room3, room4, room5])
    db.session.commit()
    
    # Create subjects
    sub1 = Subject(code='CSE101', name='Programming Fundamentals', type='Theory', 
                  lecture_hours=3, practical_hours=2, credits=4, department_id=dept1.id)
    sub2 = Subject(code='CSE102', name='Data Structures', type='Theory',
                  lecture_hours=3, practical_hours=2, credits=4, department_id=dept1.id)
    sub3 = Subject(code='CSE103', name='Database Management', type='Theory',
                  lecture_hours=3, practical_hours=2, credits=4, department_id=dept1.id)
    sub4 = Subject(code='MAT101', name='Engineering Mathematics', type='Theory',
                  lecture_hours=4, practical_hours=0, credits=3)
    db.session.add_all([sub1, sub2, sub3, sub4])
    db.session.commit()
    
    # Create class
    class1 = Class(name='Computer Engineering', code='CO-1', year='FY', 
                  department_id=dept1.id, semester=1, strength=60)
    db.session.add(class1)
    db.session.flush()
    
    # Create batches
    for i in range(1, 4):
        batch = Batch(name=f'TB{i}', code=f'CO-1_TB{i}', class_id=class1.id, mentor_id=faculty1.id if i == 1 else faculty2.id if i == 2 else faculty3.id)
        db.session.add(batch)
    
    db.session.commit()
    
    # Assign subjects to class
    cs1 = ClassSubject(class_id=class1.id, subject_id=sub1.id, faculty_id=faculty1.id,
                      lecture_slots_per_week=3, practical_slots_per_week=2)
    cs2 = ClassSubject(class_id=class1.id, subject_id=sub2.id, faculty_id=faculty2.id,
                      lecture_slots_per_week=3, practical_slots_per_week=2)
    cs3 = ClassSubject(class_id=class1.id, subject_id=sub3.id, faculty_id=faculty1.id,
                      lecture_slots_per_week=3, practical_slots_per_week=2)
    cs4 = ClassSubject(class_id=class1.id, subject_id=sub4.id, faculty_id=faculty3.id,
                      lecture_slots_per_week=4, practical_slots_per_week=0)
    db.session.add_all([cs1, cs2, cs3, cs4])
    db.session.commit()
    
    flash('Sample data initialized successfully!', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)