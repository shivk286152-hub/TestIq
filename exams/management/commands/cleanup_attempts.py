"""
Management command to clean up old attempt data for free users.
Deletes detailed answers after 7 days while preserving summary data for rankings.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from exams.models import MockTestAttempt, UserAnswer
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Clean up old attempt data for free users (deletes detailed answers after 7 days)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without actually deleting data (just show what would be deleted)',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days after which to delete details (default: 7)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        days = options['days']
        verbose = options['verbose']
        
        # Calculate cutoff date
        cutoff_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"ATTEMPT CLEANUP COMMAND")
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE RUN'}")
        self.stdout.write(f"Delete details older than: {days} days (before {cutoff_date.strftime('%Y-%m-%d %H:%M')})")
        self.stdout.write(f"{'='*60}\n")
        
        # Find attempts that need cleanup
        attempts_to_clean = MockTestAttempt.objects.filter(
            is_paid_user=False,
            has_detailed_data=True,
            submitted_at__lt=cutoff_date,
            is_completed=True
        ).select_related('user', 'mock_test')
        
        count = attempts_to_clean.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS("✓ No attempts need cleaning at this time."))
            return
        
        self.stdout.write(self.style.WARNING(f"Found {count} attempts to clean up:\n"))
        
        # Show what will be deleted
        if verbose:
            for i, attempt in enumerate(attempts_to_clean[:10], 1):
                days_old = (timezone.now() - attempt.submitted_at).days
                answer_count = UserAnswer.objects.filter(attempt=attempt).count()
                self.stdout.write(f"  {i}. Attempt #{attempt.id} - {attempt.user.username} - {attempt.mock_test.title}")
                self.stdout.write(f"     Date: {attempt.submitted_at.strftime('%Y-%m-%d')} ({days_old} days old)")
                self.stdout.write(f"     Answers to delete: {answer_count}\n")
            
            if count > 10:
                self.stdout.write(f"  ... and {count - 10} more attempts\n")
        
        # Ask for confirmation if live run
        if not dry_run:
            self.stdout.write(self.style.WARNING(f"You are about to PERMANENTLY DELETE detailed answers for {count} attempts."))
            confirm = input("Are you sure you want to continue? (yes/no): ")
            
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR("Operation cancelled."))
                return
        
        # Perform cleanup
        cleaned_count = 0
        total_deleted = 0
        
        for attempt in attempts_to_clean:
            with transaction.atomic():
                answers = UserAnswer.objects.filter(attempt=attempt)
                answer_count = answers.count()
                
                if dry_run:
                    self.stdout.write(f"[DRY RUN] Would delete {answer_count} answers for attempt #{attempt.id}")
                    cleaned_count += 1
                    total_deleted += answer_count
                else:
                    deleted = answers.delete()[0]
                    attempt.has_detailed_data = False
                    attempt.details_deleted_at = timezone.now()
                    attempt.save()
                    
                    cleaned_count += 1
                    total_deleted += deleted
                    self.stdout.write(f"  ✓ Deleted {deleted} answers for attempt #{attempt.id}")
        
        # Summary
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"CLEANUP SUMMARY")
        self.stdout.write(f"{'='*60}")
        
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"DRY RUN: Would clean {cleaned_count} attempts and delete {total_deleted} answers"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✓ Successfully cleaned {cleaned_count} attempts"))
            self.stdout.write(self.style.SUCCESS(f"✓ Deleted {total_deleted} detailed answers"))
        
        self.stdout.write(f"{'='*60}\n")