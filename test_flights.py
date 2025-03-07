from fast_flights import (
    create_filter, 
    get_flights_from_filter, 
    get_top_sorted_flights,
    get_best_flights_across_dates,
    FlightData, 
    Passengers
)
from datetime import datetime, timedelta
from collections import defaultdict

def analyze_flights(results):
    """Analyze flight data and return statistics"""
    airlines = defaultdict(int)
    prices = []
    stops = defaultdict(int)
    best_flights = 0
    
    for flight in results.flights:
        airlines[flight.name] += 1
        prices.append(float(flight.price.replace("$", "").replace(",", "")))
        stops[flight.stops] += 1
        if flight.is_best:
            best_flights += 1
    
    return {
        "total_flights": len(results.flights),
        "best_flights": best_flights,
        "airlines": dict(airlines),
        "price_range": f"${min(prices):,.2f} - ${max(prices):,.2f}",
        "avg_price": f"${sum(prices)/len(prices):,.2f}",
        "stops": dict(stops)
    }

def print_results(results, mode_name):
    """Helper function to print results in a readable format"""
    stats = analyze_flights(results)
    
    print(f"\n=== {mode_name} Results ===")
    print(f"Current Price: {results.current_price}")
    print(f"Number of Flights Found: {stats['total_flights']}")
    print(f"'Best' Flights: {stats['best_flights']}")
    print(f"Price Range: {stats['price_range']}")
    print(f"Average Price: {stats['avg_price']}")
    
    print("\nAirlines:")
    for airline, count in sorted(stats['airlines'].items()):
        print(f"  {airline}: {count} flights")
    
    print("\nStops Distribution:")
    for stops, count in sorted(stats['stops'].items()):
        print(f"  {stops} stops: {count} flights")
    
    print("\nSample of Flights:")
    print("-" * 50)
    for i, flight in enumerate(results.flights[:5], 1):  # Show first 5 flights
        print(f"Flight {i}:")
        print(f"  Airline: {flight.name}")
        print(f"  Duration: {flight.duration}")
        print(f"  Price: {flight.price}")
        print(f"  Stops: {flight.stops}")
        print(f"  Best Flight: {flight.is_best}")
        print("-" * 50)
    
    return stats

def test_common():
    """Test common mode (direct HTTP request)"""
    future_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
    
    filter = create_filter(
        flight_data=[
            FlightData(
                date=future_date,
                from_airport="LAX",  # Los Angeles
                to_airport="JFK",    # New York
            )
        ],
        trip="one-way",
        passengers=Passengers(adults=2, children=1, infants_in_seat=0, infants_on_lap=0),
        seat="economy",
        max_stops=1,
    )
    print("\n=== Common Mode Test (Direct HTTP) ===")
    print("Base64 encoded filter:")
    print(filter.as_b64().decode("utf-8"))
    results = get_flights_from_filter(filter, mode="common")
    return print_results(results, "Common Mode")

def test_local():
    """Test local mode (local Playwright)"""
    future_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
    
    filter = create_filter(
        flight_data=[
            FlightData(
                date=future_date,
                from_airport="LAX",
                to_airport="JFK",
            )
        ],
        trip="one-way",
        passengers=Passengers(adults=2, children=1, infants_in_seat=0, infants_on_lap=0),
        seat="economy",
        max_stops=1,
    )
    print("\n=== Local Mode Test (Local Playwright) ===")
    print("Base64 encoded filter:")
    print(filter.as_b64().decode("utf-8"))
    results = get_flights_from_filter(filter, mode="local")
    return print_results(results, "Local Mode")

def test_sorted_flights():
    """Test the get_top_sorted_flights function with price sorting"""
    future_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
    
    flight_data = [
        FlightData(
            date=future_date,
            from_airport="LAX",
            to_airport="JFK",
        )
    ]
    passengers = Passengers(adults=2, children=1, infants_in_seat=0, infants_on_lap=0)
    
    print(f"\n=== Testing Price Sorting ===")
    results = get_top_sorted_flights(
        flight_data=flight_data,
        trip="one-way",
        passengers=passengers,
        seat="economy",
        fetch_mode="local",  # Using local mode for consistent results
        max_stops=1,
        sort_method="price",
    )
    
    # Print results with additional sorting-specific information
    stats = analyze_flights(results)
    print(f"Total Flights Selected: {stats['total_flights']}")
    print(f"Flights by Stop Count:")
    for stops, count in sorted(stats['stops'].items()):
        print(f"  {stops} stops: {count} flights (top 5 by price)")
    
    print("\nSelected Flights:")
    print("-" * 50)
    for i, flight in enumerate(results.flights, 1):
        print(f"Flight {i}:")
        print(f"  Airline: {flight.name}")
        print(f"  Duration: {flight.duration}")
        print(f"  Price: {flight.price}")
        print(f"  Stops: {flight.stops}")
        print(f"  Best Flight: {flight.is_best}")
        print("-" * 50)

def test_date_range():
    """Test getting best flights across a date range"""
    # Set up dates (3 days from now to 5 days from now)
    start_date = datetime.now() + timedelta(days=60)
    end_date = start_date + timedelta(days=2)  # 3 days total
    
    print(f"\n=== Testing Date Range Search ===")
    print(f"Searching for flights from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Route: LAX -> JFK")
    
    results = get_best_flights_across_dates(
        start_date=start_date,
        end_date=end_date,
        from_airport="LAX",
        to_airport="JFK",
        trip="one-way",
        passengers=Passengers(adults=2, children=1, infants_in_seat=0, infants_on_lap=0),
        seat="economy",
        fetch_mode="local",  # Using local mode for consistent results
        max_stops=1,
        sort_method="price",
    )
    
    # Print results
    stats = analyze_flights(results)
    print(f"Price Level: {results.current_price}")
    print(f"Total Selected Flights: {stats['total_flights']}")
    
    print("\nSelected Flights:")
    print("-" * 70)
    for i, flight in enumerate(results.flights, 1):
        print(f"Flight {i}:")
        print(f"  Date: {flight.date}")
        print(f"  Airline: {flight.name}")
        print(f"  Duration: {flight.duration}")
        print(f"  Price: {flight.price}")
        print(f"  Stops: {flight.stops}")
        print(f"  Best Flight: {flight.is_best}")
        print("-" * 70)

if __name__ == "__main__":
    future_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
    print("Starting flight search tests...")
    print(f"(Testing LAX->JFK flights for {future_date})")
    
    # print("\n=== Testing Regular Flight Search ===")
    # print("(Testing both direct HTTP and local Playwright methods)")
    
    # common_stats = test_common()    # Test direct HTTP request
    # local_stats = test_local()      # Test local Playwright
    
    # print("\n=== Mode Comparison ===")
    # print(f"Common Mode Flights: {common_stats['total_flights']} ({common_stats['best_flights']} best)")
    # print(f"Local Mode Flights: {local_stats['total_flights']} ({local_stats['best_flights']} best)")
    
    # common_airlines = set(common_stats['airlines'].keys())
    # local_airlines = set(local_stats['airlines'].keys())
    
    # print("\nAirlines only in Common Mode:", common_airlines - local_airlines)
    # print("Airlines only in Local Mode:", local_airlines - common_airlines)
    
    # print("\n=== Testing Sorted Flights ===")
    # test_sorted_flights()    # Test the sorting functionality
    
    print("\n=== Testing Date Range Search ===")
    test_date_range()       # Test the new date range functionality
    
    print("\nTests completed!") 