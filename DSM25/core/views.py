from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.management import call_command

# Create your views here.
def home(request):
    return render(request, 'core/home.html')

def management(request):
    return render(request, 'core/management.html')

def import_data(request):
    if request.method == 'POST':
        try:
            call_command('import_data', populate=True)
            messages.success(request, 'import_data command ran successfully!')
        except Exception as e:
            messages.error(request, f'Error: {e}')
        return redirect('management')

def run_score_diabetes(request):
    if request.method == 'POST':
        try:
            call_command("score_diabetes", fraction=0.05)
            messages.success(request, 'score_diabetes command ran successfully!')
        except Exception as e:
            messages.error(request, f'Error: {e}')
        return redirect('management')

def run_note_classifier(request):
    if request.method == 'POST':
        try:
            call_command("note_classifier", min_labels=50)
            messages.success(request, 'note_classifier command ran successfully!')
        except Exception as e:
            messages.error(request, f'Error: {e}')
        return redirect('management')