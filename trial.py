# This is a trial script to test the bioreactor website.
import os

# Add numbers
num1 = 34
num2 = 76
sum_result = num1 + num2
print(f"The sum of {num1} and {num2} is {sum_result}")

double_sum = 2 * sum_result

# Ensure output directory exists in the same directory as this script
script_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(script_dir, 'output')
os.makedirs(output_dir, exist_ok=True)

# Write double the sum to a file in the output directory
output_file = os.path.join(output_dir, 'double_sum.txt')
with open(output_file, 'w') as f:
    f.write(str(double_sum) + '\n')
