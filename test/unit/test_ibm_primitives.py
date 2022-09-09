# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for primitive classes."""

import sys
from unittest.mock import MagicMock, patch, ANY
from dataclasses import asdict

from qiskit.test.reference_circuits import ReferenceCircuits
from qiskit.quantum_info import SparsePauliOp
from qiskit_ibm_runtime import Sampler, Estimator, Options, Session
from qiskit_ibm_runtime.ibm_backend import IBMBackend
import qiskit_ibm_runtime.session as session_pkg
from ..ibm_test_case import IBMTestCase


class TestPrimitives(IBMTestCase):
    """Class for testing the Sampler class."""

    @classmethod
    def setUpClass(cls):
        cls.qx = ReferenceCircuits.bell()
        cls.obs = SparsePauliOp.from_list([("IZ", 1)])
        return super().setUpClass()

    def tearDown(self) -> None:
        super().tearDown()
        session_pkg._DEFAULT_SESSION = None

    def test_skip_transpilation(self):
        """Test skip_transpilation is hornored."""
        primitives = [Sampler, Estimator]
        for cls in primitives:
            with self.subTest(primitive=cls):
                inst = cls(session=MagicMock(spec=Session), skip_transpilation=True)
                self.assertTrue(inst.options.transpilation.skip_transpilation)

    def test_skip_transpilation_overwrite(self):
        """Test overwriting skip_transpilation."""
        options = Options()
        options.transpilation.skip_transpilation = False
        primitives = [Sampler, Estimator]
        for cls in primitives:
            with self.subTest(primitive=cls):
                inst = cls(
                    session=MagicMock(spec=Session),
                    options=options,
                    skip_transpilation=True,
                )
                self.assertFalse(inst.options.transpilation.skip_transpilation)

    def test_dict_options(self):
        """Test passing a dictionary as options."""
        options_vars = [
            {},
            {
                "resilience_level": 1,
                "transpilation": {"seed_transpiler": 24},
                "execution": {"shots": 100, "init_qubits": True},
                "log_level": "INFO",
            },
            {"transpilation": {}},
        ]
        primitives = [Sampler, Estimator]
        for cls in primitives:
            for options in options_vars:
                with self.subTest(primitive=cls, options=options):
                    inst = cls(session=MagicMock(spec=Session), options=options)
                    expected = asdict(Options())
                    self._update_dict(expected, options)
                    self.assertDictEqual(expected, asdict(inst.options))

    def test_backend_in_options(self):
        """Test specifying backend in options."""
        primitives = [Sampler, Estimator]
        backend_name = "ibm_gotham"
        backend = MagicMock(spec=IBMBackend)
        backend.name = backend_name
        backends = [backend_name, backend]
        for cls in primitives:
            for backend in backends:
                with self.subTest(primitive=cls, backend=backend):
                    options = {"backend": backend}
                    inst = cls(service=MagicMock(), options=options)
                    self.assertEqual(inst.session.backend(), backend_name)

    @patch("qiskit_ibm_runtime.session.Session")
    @patch("qiskit_ibm_runtime.session.QiskitRuntimeService")
    def test_backend_str_as_session(self, _, mock_session):
        """Test specifying a backend name as session."""
        primitives = [Sampler, Estimator]
        backend_name = "ibm_gotham"

        for cls in primitives:
            with self.subTest(primitive=cls):
                _ = cls(session=backend_name)
                mock_session.assert_called_with(service=ANY, backend=backend_name)

    def test_backend_as_session(self):
        """Test specifying a backend as session."""
        primitives = [Sampler, Estimator]
        backend = MagicMock(spec=IBMBackend)
        backend.name = "ibm_gotham"
        backend.service = MagicMock()

        for cls in primitives:
            with self.subTest(primitive=cls):
                inst = cls(session=backend)
                self.assertEqual(inst.session.backend(), backend.name)

    @patch("qiskit_ibm_runtime.session.Session")
    @patch("qiskit_ibm_runtime.session.QiskitRuntimeService")
    def test_default_session(self, *_):
        """Test a session is created if not passed in."""
        sampler = Sampler()
        self.assertIsNotNone(sampler.session)
        estimator = Estimator()
        self.assertEqual(estimator.session, sampler.session)

    def test_run_inputs_default(self):
        """Test run using default options."""
        session = MagicMock(spec=Session)
        options_vars = [
            (Options(resilience_level=9), {"resilience_settings": {"level": 9}}),
            (
                Options(optimization_level=8),
                {"transpilation_settings": {"optimization_settings": {"level": 8}}},
            ),
            (
                {"transpilation": {"seed_transpiler": 24}, "execution": {"shots": 100}},
                {
                    "transpilation_settings": {"seed_transpiler": 24},
                    "run_options": {"shots": 100},
                },
            ),
        ]
        primitives = [Sampler, Estimator]
        for cls in primitives:
            for options, expected in options_vars:
                with self.subTest(primitive=cls, options=options):
                    inst = cls(session=session, options=options)
                    inst.run(self.qx, observables=self.obs)
                    if sys.version_info >= (3, 8):
                        inputs = session.run.call_args.kwargs["inputs"]
                    else:
                        _, kwargs = session.run.call_args
                        inputs = kwargs["inputs"]

                    self._assert_dict_paritally_equal(inputs, expected)

    def test_run_inputs_updated_default(self):
        """Test run using updated default options."""
        session = MagicMock(spec=Session)
        primitives = [Sampler, Estimator]
        for cls in primitives:
            with self.subTest(primitive=cls):
                inst = cls(session=session)
                inst.options.resilience_level = 1
                inst.options.optimization_level = 2
                inst.options.execution.shots = 3
                inst.run(self.qx, observables=self.obs)
                if sys.version_info >= (3, 8):
                    inputs = session.run.call_args.kwargs["inputs"]
                else:
                    _, kwargs = session.run.call_args
                    inputs = kwargs["inputs"]
                self._assert_dict_paritally_equal(
                    inputs,
                    {
                        "resilience_settings": {"level": 1},
                        "transpilation_settings": {
                            "optimization_settings": {"level": 2}
                        },
                        "run_options": {"shots": 3},
                    },
                )

    def test_run_inputs_overwrite(self):
        """Test run using overwritten options."""
        session = MagicMock(spec=Session)
        options_vars = [
            ({"resilience_level": 9}, {"resilience_settings": {"level": 9}}),
            ({"shots": 200}, {"run_options": {"shots": 200}}),
            (
                {"optimization_level": 8},
                {"transpilation_settings": {"optimization_settings": {"level": 8}}},
            ),
            (
                {"seed_transpiler": 24, "optimization_level": 8},
                {
                    "transpilation_settings": {
                        "optimization_settings": {"level": 8},
                        "seed_transpiler": 24,
                    }
                },
            ),
        ]
        primitives = [Sampler, Estimator]
        for cls in primitives:
            for options, expected in options_vars:
                with self.subTest(primitive=cls, options=options):
                    inst = cls(session=session)
                    inst.run(self.qx, observables=self.obs, **options)
                    if sys.version_info >= (3, 8):
                        inputs = session.run.call_args.kwargs["inputs"]
                    else:
                        _, kwargs = session.run.call_args
                        inputs = kwargs["inputs"]
                    self._assert_dict_paritally_equal(inputs, expected)
                    self.assertDictEqual(asdict(inst.options), asdict(Options()))

    def _update_dict(self, dict1, dict2):
        for key, val in dict1.items():
            if isinstance(val, dict):
                self._update_dict(val, dict2.pop(key, {}))
            elif key in dict2.keys():
                dict1[key] = dict2.pop(key)

    def _assert_dict_paritally_equal(self, dict1, dict2):
        for key, val in dict2.items():
            if isinstance(val, dict):
                self._assert_dict_paritally_equal(dict1.get(key), val)
            elif key in dict1:
                self.assertEqual(val, dict1[key])