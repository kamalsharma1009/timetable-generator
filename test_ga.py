import app
from app import db, Class, GeneticAlgorithmTimetable, Room

with app.app.app_context():
    # Find a class with subjects
    test_class = Class.query.first()
    if test_class:
        print(f"Testing timetable generation for class: {test_class.name} (ID: {test_class.id})")
        # Ensure rooms exist
        rooms = Room.query.all()
        if not rooms:
            print("No rooms found. This could be the issue!")
        else:
            print(f"Found {len(rooms)} rooms.")
            
        print("Running GA...")
        try:
            ga = GeneticAlgorithmTimetable(test_class.id)
            solution = ga.evolve(population_size=10, generations=10)
            
            if solution:
                print(f"Solution found! Best fitness: {ga.best_fitness}")
                print(f"Lectures: {len(solution.get('lectures', []))}")
                print(f"Practicals: {len(solution.get('practicals', []))}")
                print(f"Mentoring: {len(solution.get('mentoring', []))}")
            else:
                print("No solution returned from evolve().")
        except Exception as e:
            print(f"Exception during GA: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("No classes found in database.")
