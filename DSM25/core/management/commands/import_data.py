
from django.core.management.base import BaseCommand
import os
import csv
from core.models import Customer
from django.utils.dateparse import parse_date
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Populate the database with data.'

    def add_arguments(self, parser):
        parser.add_argument('--populate', action='store_true', help='Populate database with loaded data')

    def handle(self, *args, **options):
        if options['populate']:
            self.stdout.write(self.style.SUCCESS('Populating database...'))
            self.populate_database()

    def populate_database(self):
        # Path to the CSV file
        # Find the DSM25 base directory
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # If 'core' is in the path, go up one more level to DSM25
        if os.path.basename(base_dir) == 'core':
            base_dir = os.path.dirname(base_dir)
        csv_path = os.path.join(base_dir, 'data', 'raw_test', 'patient_info.csv')

        # Common prefixes/suffixes
        SUFFIXES = ["MR.", "MRS.", "MS.", "DR.", "MISS", "MR", "MRS", "MS", "DR"]

        def clean_name(name):
            # Remove extra spaces and normalize case
            name = name.strip()
            parts = name.split()
            suffix = ""
            # Check for prefix/suffix
            if parts and parts[0].replace('.', '').upper() in [s.replace('.', '') for s in SUFFIXES]:
                suffix = parts[0].title().replace('.', '')
                parts = parts[1:]
            # If still more than 2 parts, assume first is first name, last is last name, middle is middle initial
            first = parts[0].title() if len(parts) > 0 else ""
            last = parts[-1].title() if len(parts) > 1 else ""
            middle = parts[1][0].upper() if len(parts) > 2 and parts[1] else ""
            return first, last, middle, suffix

        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            count = 0
            for row in reader:
                name = row.get('Name', '')
                gender = row.get('Gender', '')
                first, last, middle, suffix = clean_name(name)

                Customer.objects.create(
                    CustFirstName=first,
                    CustLastName=last,
                    CustMiddleInit=middle,
                    CustSuffix=suffix,
                    Gender=gender.title(),
                )
                count += 1
            print(f"Database population completed. {count} customers added. loading Patient_lab...")

        # Populate Patient_lab
        lab_csv_path = os.path.join(base_dir, 'data', 'raw_test', 'patient_lab.csv')
        from core.models import Patient_lab

        with open(lab_csv_path, newline='', encoding='utf-8') as labfile:
            lab_reader = csv.DictReader(labfile)
            lab_count = 0
            for row in lab_reader:
                # The first column is the index, which should match the Customer's Cust_id (starting from 1)
                try:
                    patient_index = int(row.get('', None))
                except Exception:
                    continue
                cust_id = patient_index + 1
                try:
                    customer = Customer.objects.get(Cust_id=cust_id)
                except Customer.DoesNotExist:
                    continue
                # Convert Smoking_Status to boolean
                smoking = row.get('Smoking_Status', '').strip().lower()
                smoking_bool = True if smoking == 'smoker' else False
                Patient_lab.objects.create(
                    Patient_id=customer,
                    Age=int(float(row.get('Age', 0))),
                    BMI=float(row.get('BMI', 0)),
                    Systolic_BP=float(row.get('Systolic_BP', 0)),
                    Diastolic_BP=float(row.get('Diastolic_BP', 0)),
                    Total_Cholesterol=float(row.get('Total_Cholesterol', 0)),
                    HDL_Cholesterol=float(row.get('HDL_Cholesterol', 0)),
                    LDL_Cholesterol=float(row.get('LDL_Cholesterol', 0)),
                    Triglycerides=float(row.get('Triglycerides', 0)),
                    Smoking_status=smoking_bool,
                    Physical_activity=row.get('Physical_Activity_Level', '')
                )
                lab_count += 1
            print(f"Database population completed. {lab_count} patient labs added. loading Clinical_note...")

        # Populate Clinical_note
        notes_csv_path = os.path.join(base_dir, 'data', 'raw_test', 'notes.csv')
        from core.models import Clinical_note

        with open(notes_csv_path, newline='', encoding='utf-8') as notesfile:
            notes_reader = csv.DictReader(notesfile)
            notes_count = 0
            for row in notes_reader:
                # The first column is the index, which should match the Customer's Cust_id (starting from 1)
                try:
                    patient_index = int(row.get('', None))
                except Exception:
                    continue
                cust_id = patient_index + 1
                try:
                    customer = Customer.objects.get(Cust_id=cust_id)
                except Customer.DoesNotExist:
                    continue
                Clinical_note.objects.create(
                    Patient_id=customer,
                    Description=row.get('description', ''),
                    Medical_specialty=row.get('medical_specialty', ''),
                    Sample_name=row.get('sample_name', ''),
                    Transcription=row.get('transcription', ''),
                    Keywords=row.get('keywords', '')
                )
                notes_count += 1
            print(f"Database population completed. {notes_count} clinical notes added. All done.")

# Kick off ML scoring right after populate
try:
    print("Scoring structured diabetes risk…")
    call_command("score_diabetes", fraction=0.05)  # already in your file

    print("Classifying notes by specialty…")
    # Train TF-IDF+LogReg if you have enough labeled notes; else keyword fallback
    call_command("score_notes", min_labels=50)
    print("Note classification done.")
except Exception as e:
    # Don’t let a scoring hiccup kill your import
    print(f"[WARN] Post-import scoring failed: {e}")
