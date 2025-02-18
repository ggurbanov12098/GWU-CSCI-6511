import unittest
import math
import tempfile
import os
from main import parse_file, can_measure, heuristic, fill, pour, a_star

class TestWaterPitcher(unittest.TestCase):
    def create_temp_file(self, contents):
        """Helper function: creates a temporary file with the given contents."""
        temp = tempfile.NamedTemporaryFile(delete=False, mode='w+t')
        temp.write(contents)
        temp.seek(0)
        temp.close()
        return temp.name

    def test_parse_file(self):
        """
        Test that the parse_file function correctly reads:
        - The comma-separated container sizes from the first line.
        - The target value from the second line.
        Also checks that an infinite container is appended.
        """
        # Create a temporary file with sizes "3,5" and target "4"
        contents = "3,5\n4\n"
        filename = self.create_temp_file(contents)
        sizes, target = parse_file(filename)
        # Check that the finite containers are correctly parsed
        self.assertEqual(sizes[:-1], [3, 5])
        # Check that the target is correctly parsed
        self.assertEqual(target, 4)
        # Ensure the infinite container was appended
        self.assertTrue(math.isinf(sizes[-1]))
        os.unlink(filename)

    def test_can_measure(self):
        """
        Test that the can_measure function determines correctly:
        - For containers [3,5] (gcd=1), any target (4) is measurable.
        - For containers [4,6] (gcd=2), target 3 is not measurable, while target 2 is.
        - With no finite containers (only an infinite container), only target 0 is measurable.
        """
        # Test with containers [3, 5]
        sizes = [3, 5, float('inf')]
        self.assertTrue(can_measure(sizes, 4))
        
        # Test with containers [4, 6]
        sizes = [4, 6, float('inf')]
        self.assertFalse(can_measure(sizes, 3))
        self.assertTrue(can_measure(sizes, 2))
        
        # Test with no finite containers: only target 0 is measurable
        sizes = [float('inf')]
        self.assertTrue(can_measure(sizes, 0))
        self.assertFalse(can_measure(sizes, 1))

    def test_heuristic(self):
        """
        Test the heuristic function that estimates the number of moves required:
        - If the target is already met, the heuristic should be 0.
        - For a given target (4) and state (0,0,0) with smallest container 3,
          the heuristic should return ceil(4/3)=2.
        """
        sizes = [3, 5, float('inf')]
        state = (0, 0, 0)
        # If goal is met (target=0), heuristic returns 0.
        self.assertEqual(heuristic(state, 0, sizes), 0)
        # With goal=4 and smallest container=3, expected heuristic is ceil(4/3)=2.
        self.assertEqual(heuristic(state, 4, sizes), 2)

    def test_fill(self):
        """
        Test the fill function which generates new states by filling one container at a time:
        - Given a state (1,0,0) and sizes [3,5], filling should yield states (3,0,0) and (1,5,0).
        """
        sizes = [3, 5, float('inf')]
        state = (1, 0, 0)
        moves = fill(state, sizes)
        # Check that filling the first container results in (3, 0, 0)
        self.assertIn((3, 0, 0), moves)
        # Check that filling the second container results in (1, 5, 0)
        self.assertIn((1, 5, 0), moves)

    def test_pour(self):
        """
        Test the pour function which generates new states by pouring water between containers:
        - From state (0,5,0) with sizes [3,5], pouring from container 1 to 0 should yield (3,2,0).
        - Also, pouring from container 1 to the infinite container should yield (0,0,5).
        """
        sizes = [3, 5, float('inf')]
        state = (0, 5, 0)
        moves = pour(state, sizes)
        # Check that pouring from container 1 to container 0 yields (3,2,0)
        self.assertIn((3, 2, 0), moves)
        # Check that pouring from container 1 to the infinite container yields (0,0,5)
        self.assertIn((0, 0, 5), moves)

    def test_a_star_unsolvable(self):
        """
        Test the overall A* algorithm for an unsolvable scenario:
        - For containers [4,6] (gcd=2) and target 3, the problem is unsolvable and should return -1.
        """
        contents = "4,6\n3\n"
        filename = self.create_temp_file(contents)
        result = a_star(filename)
        self.assertEqual(result, -1)
        os.unlink(filename)

    def test_a_star(self):
        """
        Test the A* algorithm for a scenario:
        - When the target is 0, no moves are needed, so the function should return 0.
        """
        contents = "3,5\n0\n"
        filename = self.create_temp_file(contents)
        result = a_star(filename)
        self.assertEqual(result, 0)
        os.unlink(filename)

if __name__ == "__main__":
    unittest.main()
