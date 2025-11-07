"""Check workers and simulate alerts."""
import requests

# Get workers
r = requests.get('http://localhost:8000/admin/workers')
data = r.json()

print(f"Total workers: {data['total']}\n")

for w in data['workers'][:10]:
    perf = w['performance']
    print(f"{w['name']}")
    print(f"  Bookings: {perf['total_bookings']}")
    print(f"  Rating: {perf['average_rating']}")
    print(f"  Recent coaching: {perf['recent_coaching']}")
    print()

# Get alerts
print("\n" + "=" * 60)
print("ALERTS:")
print("=" * 60)
r = requests.get('http://localhost:8000/admin/alerts')
alerts_data = r.json()
print(f"Total alerts: {alerts_data['total']}")

if alerts_data['alerts']:
    for alert in alerts_data['alerts']:
        print(f"\n{alert['type'].upper()} - {alert['severity']}")
        print(f"  Worker: {alert['worker_name']}")
        print(f"  {alert['message']}")
