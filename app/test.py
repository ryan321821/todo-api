import math
import tkinter as tk
from tkinter import messagebox


def add(a: int, b: int) -> int:
	"""返回两个整数的和。"""
	return a + b


def calculate(a: float, b: float, operator: str) -> float:
	"""根据运算符执行基本四则运算。"""
	if operator == "+":
		return a + b
	if operator == "-":
		return a - b
	if operator == "*":
		return a * b
	if operator == "/":
		if b == 0:
			raise ZeroDivisionError("除数不能为零")
		return a / b
	raise ValueError(f"不支持的运算符: {operator}")


def scientific_calculate(value: float, operator: str) -> float:
	"""执行科学计算器的一元运算；三角函数的输入单位为角度。"""
	if operator == "sin":
		return math.sin(math.radians(value))
	if operator == "cos":
		return math.cos(math.radians(value))
	if operator == "tan":
		return math.tan(math.radians(value))
	if operator == "sqrt":
		return math.sqrt(value)
	if operator == "log10":
		return math.log10(value)
	if operator == "ln":
		return math.log(value)
	if operator == "exp":
		return math.exp(value)
	if operator == "factorial":
		if not value.is_integer() or value < 0:
			raise ValueError("阶乘仅支持非负整数")
		return float(math.factorial(int(value)))
	if operator == "abs":
		return abs(value)
	raise ValueError(f"不支持的科学运算符: {operator}")


def create_calculator() -> tk.Tk:
	"""创建一个使用上述计算函数的简单科学计算器界面。"""
	root = tk.Tk()
	root.title("科学计算器")
	root.resizable(False, False)

	first_value = tk.StringVar()
	second_value = tk.StringVar()
	result = tk.StringVar()

	def show_result(value: float) -> None:
		result.set(str(value))

	def calculate_binary(operator: str) -> None:
		try:
			a = float(first_value.get())
			b = float(second_value.get())
			show_result(calculate(a, b, operator))
		except (ValueError, ZeroDivisionError) as error:
			messagebox.showerror("计算错误", str(error))

	def calculate_unary(operator: str) -> None:
		try:
			value = float(first_value.get())
			show_result(scientific_calculate(value, operator))
		except (ValueError, OverflowError) as error:
			messagebox.showerror("计算错误", str(error))

	frame = tk.Frame(root, padx=12, pady=12)
	frame.pack()

	tk_label = tk.Label
	tk_label(frame, text="第一个数").grid(row=0, column=0, sticky="w")
	tk.Entry(frame, textvariable=first_value, width=24).grid(row=0, column=1, columnspan=4, pady=4)
	tk_label(frame, text="第二个数").grid(row=1, column=0, sticky="w")
	tk.Entry(frame, textvariable=second_value, width=24).grid(row=1, column=1, columnspan=4, pady=4)
	tk_label(frame, text="结果").grid(row=2, column=0, sticky="w")
	tk.Entry(frame, textvariable=result, width=24, state="readonly").grid(row=2, column=1, columnspan=4, pady=4)

	for column, operator in enumerate(("+", "-", "*", "/")):
		tk.Button(frame, text=operator, width=5,
				  command=lambda op=operator: calculate_binary(op)).grid(row=3, column=column + 1, padx=2, pady=8)

	for column, operator in enumerate(("sin", "cos", "tan", "sqrt", "log10")):
		tk.Button(frame, text=operator, width=6,
				  command=lambda op=operator: calculate_unary(op)).grid(row=4, column=column, padx=2, pady=2)
	for column, operator in enumerate(("ln", "exp", "factorial", "abs")):
		tk.Button(frame, text=operator, width=8,
				  command=lambda op=operator: calculate_unary(op)).grid(row=5, column=column, padx=2, pady=2)

	return root


if __name__ == "__main__":
	create_calculator().mainloop()
