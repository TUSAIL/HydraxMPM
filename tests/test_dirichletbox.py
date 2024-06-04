"""Unit tests for the NodesContainer class."""

import unittest

import jax.numpy as jnp

import pymudokon as pm


class DirichletBox(unittest.TestCase):
    """Unit tests for the DirichletBox and functions."""

    @staticmethod
    def test_init():
        """Unit test to initialize the NodesContainer class."""
        box = pm.DirichletBox.create()

        assert isinstance(box, pm.DirichletBox)

    @staticmethod
    def test_apply_on_node_moments():
        """Unit test to initialize the NodesContainer class."""
        nodes = pm.Nodes.create(
            origin=jnp.array([0.0, 0.0]),
            end=jnp.array([1.0, 1.0]),
            node_spacing=0.1
        )

        box = pm.DirichletBox.create()

        box.apply_on_nodes_moments(nodes)

        assert isinstance(box, pm.DirichletBox)


if __name__ == "__main__":
    unittest.main()
