from webilastik.scheduling import SerialExecutor

def test_serial_executor():
    print(f"test_serial_executor")
    with SerialExecutor() as executor:
        def double(x: int) -> int:
            return x* 2

        results = list(executor.map(double, [1,2,3,4,5]))
        assert results == [2,4,6,8,10]

if __name__ == "__main__":
    test_serial_executor()