import uuid
import threading
from concurrent.futures import ThreadPoolExecutor

class AttendanceJobManager:
    """
    Thread-safe in-memory job manager for asynchronous attendance processing.
    Tracks live percentage progress and human-readable status messages.
    """
    def __init__(self, max_workers=2):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.jobs = {}
        self.lock = threading.Lock()

    def create_job(self):
        job_id = uuid.uuid4().hex[:12]
        with self.lock:
            self.jobs[job_id] = {
                'job_id': job_id,
                'status': 'queued',
                'progress': 5,
                'message': 'Job created. Preparing images...',
                'result': None,
                'error': None
            }
        return job_id

    def update_job(self, job_id, progress, message, status='running'):
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id]['progress'] = progress
                self.jobs[job_id]['message'] = message
                self.jobs[job_id]['status'] = status

    def complete_job(self, job_id, result):
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id]['progress'] = 100
                self.jobs[job_id]['status'] = 'completed'
                self.jobs[job_id]['message'] = 'Classroom attendance processed successfully!'
                self.jobs[job_id]['result'] = result

    def fail_job(self, job_id, error_msg):
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id]['status'] = 'failed'
                self.jobs[job_id]['error'] = error_msg
                self.jobs[job_id]['message'] = f"Processing error: {error_msg}"

    def get_job(self, job_id):
        with self.lock:
            return self.jobs.get(job_id)

    def submit_task(self, fn, *args, **kwargs):
        """Submit a background job function to the thread pool."""
        return self.executor.submit(fn, *args, **kwargs)

# Global singleton instance
attendance_jobs = AttendanceJobManager()
