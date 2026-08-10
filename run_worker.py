"""
run_worker.py – Custom Windows-compatible ARQ worker daemon.

Bypasses the broken redis.asyncio socket connect timeout bugs on Windows + Python 3.14
by using a synchronous redis.Redis client for queue polling, and executing the async
review task inside a clean asyncio event loop.
"""
import os
import sys
import time
import asyncio
import redis as sync_redis

from arq.jobs import deserialize_job
from arq.utils import timestamp_ms
from backend.queue.worker import review_pr

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
ARQ_QUEUE = "arq:queue"
JOB_PREFIX = "arq:job:"

# Force Selector Loop policy on Windows for subprocesses/HTTP calls
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _deserialize(job_bytes: bytes):
    """Attempt deserialization using pickle (ARQ default) then msgpack/json."""
    try:
        # ARQ default uses pickle by default
        import pickle
        return deserialize_job(job_bytes, deserializer=pickle.loads)
    except Exception:
        pass
    
    try:
        # Fallback to msgpack if msgpack was used
        import msgpack
        return deserialize_job(job_bytes, deserializer=msgpack.unpackb)
    except Exception:
        pass
        
    raise RuntimeError("Unable to deserialize job bytes")


async def run_job(job_id: str, job_def) -> None:
    """Execute the job's async task function."""
    print(f"\n[Worker] ---> Executing job {job_id} ({job_def.function})")
    
    # We only handle "review_pr" in this agent worker
    if job_def.function == "review_pr":
        payload = job_def.kwargs.get("payload") or {}
        # Pass delivery_id to payload so it tracks idempotency
        payload["delivery_id"] = job_id
        
        try:
            t0 = time.monotonic()
            result = await review_pr({}, payload)
            duration = time.monotonic() - t0
            print(f"[Worker] <--- Completed job {job_id} in {duration:.2f}s. Result: {result}")
        except Exception as e:
            print(f"[Worker] <--- Failed job {job_id}: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"[Worker] Unknown job function: {job_def.function}")


def main():
    print(f"Connecting to Redis at {REDIS_URL}...")
    r = sync_redis.Redis.from_url(REDIS_URL)
    
    try:
        r.ping()
        print("Connected to Redis successfully.")
    except Exception as e:
        print(f"Error: Could not connect to Redis: {e}")
        sys.exit(1)

    print("ARQ Worker Daemon started. Listening for jobs...")

    while True:
        try:
            # Poll the sorted set for jobs ready to run (score <= current time in ms)
            now_ms = timestamp_ms()
            jobs = r.zrangebyscore(ARQ_QUEUE, 0, now_ms, start=0, num=1)
            
            if not jobs:
                # No jobs ready, sleep and poll again
                time.sleep(1.0)
                continue
                
            job_id_bytes = jobs[0]
            job_id = job_id_bytes.decode("utf-8")
            job_key = f"{JOB_PREFIX}{job_id}"
            
            # Use a transaction/pipeline to fetch the job details and remove it from the queue atomatically
            pipe = r.pipeline()
            pipe.get(job_key)
            pipe.zrem(ARQ_QUEUE, job_id_bytes)
            job_bytes, removed = pipe.execute()
            
            if not job_bytes:
                # Job expired or was removed by another worker
                continue
                
            if not removed:
                # Another worker picked it up first
                continue
                
            # Deserialize job details
            try:
                job_def = _deserialize(job_bytes)
            except Exception as e:
                print(f"[Worker Error] Deserialization failed for job {job_id}: {e}")
                r.delete(job_key)
                continue
                
            # Run the job
            asyncio.run(run_job(job_id, job_def))
            
            # Clean up the job metadata key
            r.delete(job_key)
            
        except KeyboardInterrupt:
            print("\nShutting down ARQ Worker Daemon.")
            break
        except Exception as e:
            print(f"[Worker Error] Error in polling loop: {e}")
            time.sleep(2.0)


if __name__ == "__main__":
    main()
