"""
Management command to set up a cron job for daily cleanup.
"""

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Setup daily cron job for cleaning up old attempt data'
    
    def handle(self, *args, **options):
        project_path = "/media/dharmi/Acer4/shivkumar/TestIq"
        python_path = "/media/dharmi/Acer4/shivkumar/TestIq/venv/bin/python"
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write("CRON JOB SETUP INSTRUCTIONS")
        self.stdout.write("="*60)
        self.stdout.write("\n1. Create logs directory:")
        self.stdout.write(f"\n   mkdir -p {project_path}/logs")
        
        self.stdout.write("\n\n2. Open crontab editor:")
        self.stdout.write("\n   crontab -e")
        
        self.stdout.write("\n\n3. Add this line to run daily at 2 AM:")
        self.stdout.write(f"\n   0 2 * * * cd {project_path} && {python_path} manage.py cleanup_attempts --days=7 >> {project_path}/logs/cleanup.log 2>&1")
        
        self.stdout.write("\n\n4. Save and exit the editor")
        
        self.stdout.write("\n\n5. Verify it's added:")
        self.stdout.write("\n   crontab -l")
        
        self.stdout.write("\n\n6. Test the command manually:")
        self.stdout.write("\n   python manage.py cleanup_attempts --dry-run --verbose")
        
        self.stdout.write("\n\n7. Check logs after it runs:")
        self.stdout.write(f"\n   cat {project_path}/logs/cleanup.log")
        
        self.stdout.write("\n" + "="*60 + "\n")