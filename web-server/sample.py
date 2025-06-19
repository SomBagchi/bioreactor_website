# This is a trial script to test the bioreactor website.
import os
import socket

# Add numbers
num1 = 48
num2 = 52
sum_result = num1 + num2
print(f"The sum of {num1} and {num2} is {sum_result}")

def get_ip_address():
    try:
        # Get the hostname
        hostname = socket.gethostname()
        # Get the IP address
        ip_address = socket.gethostbyname(hostname)
        return ip_address
    except Exception as e:
        return f"Could not get IP address: {e}"

# Print the IP address
ip = get_ip_address()
print(f"Device IP address: {ip}")


triple_sum = 3 * sum_result

# Ensure output directory exists in the same directory as this script
script_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(script_dir, 'output')
os.makedirs(output_dir, exist_ok=True)

# Write double the sum to a file in the output directory
output_file = os.path.join(output_dir, 'double_sum.txt')
with open(output_file, 'w') as f:
    f.write(str(triple_sum) + '\n')
