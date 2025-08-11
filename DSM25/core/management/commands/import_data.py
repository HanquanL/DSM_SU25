from django.core.management.base import BaseCommand
import kagglehub
import os

class Command(BaseCommand):
    help = 'Download and populate the database with data.'

    def add_arguments(self, parser):
        parser.add_argument('--download', action='store_true', help='Download data files')
        parser.add_argument('--populate', action='store_true', help='Populate database with loaded data')

    def handle(self, *args, **options):
        if options['download']:
            self.stdout.write(self.style.SUCCESS('Downloading data...'))
            self.download_data()
        if options['populate']:
            self.stdout.write(self.style.SUCCESS('Populating database...'))
            self.populate_database()
        if not any([options['download'], options['populate']]):
            self.stdout.write(self.style.WARNING('No action specified. Use --download or --populate.'))

    def download_data(self):
        import shutil
        # Save to P4_APP/DSM25/data/raw/ from the project root
        dest_path = os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '..', 'data', 'raw'))
        os.makedirs(dest_path, exist_ok=True)

        patient_path = kagglehub.dataset_download("prasad22/healthcare-dataset", path='healthcare_dataset.csv')
        note_path = kagglehub.dataset_download("tboyle10/medicaltranscriptions", path='mtsamples.csv')
        health_path = kagglehub.dataset_download("rajagrawal7089/healthcare", path='Health.csv')

        shutil.move(patient_path, os.path.join(dest_path, 'patient_info.csv'))
        shutil.move(note_path, os.path.join(dest_path, 'note.csv'))
        shutil.move(health_path, os.path.join(dest_path, 'lab.csv'))
        self.stdout.write(self.style.SUCCESS(f"Files downloaded and renamed to {dest_path}"))

    def populate_database(self):
        # TODO: Implement database population logic
        pass
