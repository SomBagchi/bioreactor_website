import os

# Add numbers
num1 = 34
num2 = 76
sum_result = num1 + num2
print(f"The sum of {num1} and {num2} is {sum_result}")

double_sum = 2 * sum_result

# Ensure output directory exists
output_dir = 'output'
os.makedirs(output_dir, exist_ok=True)

# Write double the sum to a file
output_file = os.path.join(output_dir, 'double_sum.txt')
with open(output_file, 'w') as f:
    f.write(str(double_sum) + '\n')
