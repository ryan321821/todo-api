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
