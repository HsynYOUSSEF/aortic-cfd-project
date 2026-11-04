"""Small geometry/coordinate tests; not a CFD or anatomical validation."""
import tempfile
import unittest
from pathlib import Path
import numpy as np
import vtk
from reconstruct_mask import repair, surface


class ReconstructionTests(unittest.TestCase):
    def test_retains_branch_sections_and_removes_island(self):
        source = np.zeros((14, 24, 24), bool)
        source[1:13, 5:11, 4:9] = True
        source[1:13, 5:11, 15:20] = True
        source[1:5, 5:11, 4:20] = True
        source[7, 21, 21] = True
        repaired, _ = repair(source, np.array([.6, .8, .8]), .4)
        from scipy.ndimage import label
        self.assertEqual(label(repaired)[1], 1)
        self.assertEqual(label(repaired[10])[1], 2)
        self.assertFalse(repaired[7, 21, 21])

    def test_surface_preserves_signed_ras_coordinates(self):
        mask = np.zeros((8, 9, 10), bool); mask[2:6, 2:7, 2:8] = True
        matrix = np.diag([-2., 3., -.5]); origin = np.array([20., -10., 7.])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'test.vtp'
            result = surface(mask, matrix, origin, path)
            reader = vtk.vtkXMLPolyDataReader(); reader.SetFileName(str(path)); reader.Update()
            np.testing.assert_allclose(reader.GetOutput().GetBounds(), [5., 17., -5.5, 9.5, 4.25, 6.25])
            self.assertEqual(result['boundary_or_nonmanifold_edges'], 0)


if __name__ == '__main__':
    unittest.main()
