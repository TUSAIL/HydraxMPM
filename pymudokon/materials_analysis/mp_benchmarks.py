from typing import Tuple

import chex
import jax
import jax.numpy as jnp

from ..materials.material import Material
from .mix_control import mix_control


@chex.dataclass
class MPBenchmark:
    material: Material
    total_time: jnp.float32
    dt: jnp.float32
    load_steps: jnp.int32
    target_range: Tuple
    phi_ref: jnp.float32
    store_every: jnp.int32
    output: Tuple[str]
    L_control_stack: chex.Array
    stress_control: chex.Array
    stress_mask_indices: chex.Array

    stress_ref: chex.Array
    F_ref: chex.Array
    accumulated: Tuple[chex.Array]

    @classmethod
    def create_isochoric_shear(
        cls,
        material,
        total_time=200,
        target_range=(0.0, 0.1),
        dt=0.0001,
        store_every=50,
        pressure_control=None,
        phi_ref=0.7,
        F_ref=None,
        stress_ref=None,
        output=None,
        early_stop_iter=None,
    ):
        if stress_ref is not None:
            material = material.replace(stress_ref=stress_ref.reshape(1, 3, 3))
        else:
            stress_ref = material.stress_ref.reshape(3, 3)

        if F_ref is not None:
            F_ref = jnp.eye(3)

        load_steps = jnp.int32(total_time / dt)

        deps_dt = (target_range[1] / load_steps) / dt

        L_control_stack = (
            jnp.zeros((load_steps, 3, 3)).at[:, [0, 1], [1, 0]].set(deps_dt)
        )

        if pressure_control is None:
            stress_control = jnp.zeros((3, 3))
            stress_mask_indices = None
        else:
            mask = jnp.zeros((3, 3)).at[[0, 1, 2], [0, 1, 2]].set(1).astype(bool)
            stress_control = jnp.zeros((3, 3)).at[mask].set(-pressure_control / 3.0)
            stress_mask_indices = jnp.where(mask)

        return cls(
            material=material,
            total_time=total_time,
            load_steps=load_steps,
            dt=dt,
            target_range=target_range,
            phi_ref=phi_ref,
            stress_ref=stress_ref,
            store_every=store_every,
            output=output,
            L_control_stack=L_control_stack.at[:early_stop_iter].get(),
            stress_control=stress_control,
            stress_mask_indices=stress_mask_indices,
            F_ref=None,
            accumulated=None,
        )

    @classmethod
    def create_isochoric_shear_rate(
        cls,
        material,
        total_time=200,
        target_range=(
            0.0,
            0.1,
        ),
        dt=0.0001,
        store_every=50,
        pressure_control=None,
        phi_ref=0.7,
        F_ref=None,
        stress_ref=None,
        output=None,
        early_stop_iter=None,
    ):
        if stress_ref is not None:
            material = material.replace(stress_ref=stress_ref.reshape(1, 3, 3))
        else:
            stress_ref = material.stress_ref.reshape(3, 3)

        if F_ref is not None:
            F_ref = jnp.eye(3)

        load_steps = jnp.int32(total_time / dt)

        deps_dt_stack = jnp.linspace(target_range[0], target_range[1], load_steps)

        def get_velgrad(deps_dt):
            return jnp.zeros((3, 3)).at[[0, 1], [1, 0]].set(deps_dt)

        L_control_stack = jax.vmap(get_velgrad)(deps_dt_stack)

        if pressure_control is None:
            stress_control = jnp.zeros((3, 3))
            stress_mask_indices = None
        else:
            mask = jnp.zeros((3, 3)).at[[0, 1, 2], [0, 1, 2]].set(1).astype(bool)
            stress_control = jnp.zeros((3, 3)).at[mask].set(-pressure_control / 3.0)
            stress_mask_indices = jnp.where(mask)

        return cls(
            material=material,
            total_time=total_time,
            load_steps=load_steps,
            dt=dt,
            target_range=target_range,
            phi_ref=phi_ref,
            stress_ref=stress_ref,
            store_every=store_every,
            output=output,
            L_control_stack=L_control_stack.at[:early_stop_iter].get(),
            stress_control=stress_control,
            stress_mask_indices=stress_mask_indices,
            F_ref=None,
            accumulated=None,
        )

    def run(self):
        type(self)
        carry, accumulated = mix_control(
            material=self.material,
            dt=self.dt,
            L_control_stack=self.L_control_stack,
            stress_control=self.stress_control,
            stress_mask_indices=self.stress_mask_indices,
            stress_ref=self.stress_ref,
            F_ref=self.F_ref,
            phi_ref=self.phi_ref,
            output=self.output,
        )
        (material_next, stress_next, F_next, phi_next, step, servo_params) = carry

        accumulated_next = []
        for i, _ in enumerate(self.output):
            accumulated_next.append(accumulated[i].at[0 :: self.store_every].get())

        return self.replace(
            material=material_next,
            stress_ref=stress_next,
            F_ref=F_next,
            phi_ref=phi_next,
            accumulated=accumulated_next,
        )


# def triaxial_compression_wrapper(
#     material,
#     material_params,
#     total_time=25.0,
#     dt=0.01,
#     target=0.2,
#     confine_pressure=0.0,
#     volume_fraction=0.5,
#     stress_ref=None,
#     keys=None,
#     store_every=1,
# ):
#     if stress_ref is None:
#         stress_ref = jnp.zeros((3, 3), dtype=jnp.float32)

#     num_steps = int(total_time / dt)

#     deps_dt = (target / num_steps) / dt

#     strain_rate_stack = jnp.zeros((num_steps, 3, 3)).at[:num_steps, 0, 0].set(-deps_dt)

#     mask = jnp.zeros((3, 3)).at[[1, 2], [1, 2]].set(1).astype(bool)

#     stress_stack = (
#         jnp.zeros((num_steps, 3, 3))
#         .at[:num_steps, [0, 1, 2], [0, 1, 2]]
#         .set(-confine_pressure)
#     )

#     # material = material.create(*material_params, stress_ref=stress_ref.reshape(1, 3, 3))

#     return mix_control(
#         material=material,
#         strain_rate_stack=strain_rate_stack,
#         stress_stack=stress_stack,
#         mask=mask,
#         volume_fraction=volume_fraction,
#         stress_ref=stress_ref,
#         dt=dt,
#         store_every=store_every,
#         keys=keys,
#     )


# def isotropic_compression_wrapper(
#     material,
#     material_params,
#     total_time=25.0,
#     dt=0.0001,
#     target=0.05,
#     volume_fraction=0.5,
#     stress_ref=None,
# ):
#     raise NotImplementedError("Isotropic compression not implemented yet")


#     if stress_ref is None:
#         stress_ref = jnp.zeros((3, 3), dtype=jnp.float32)

#     num_steps = int(total_time / dt)

#     deps_xx_yy_zz = target / num_steps
#     strain_rate_stack = jnp.zeros((num_steps, 3, 3)).at[:num_steps, (0, 1, 2), (0, 1, 2)].set(-deps_xx_yy_zz)

#     mask = jnp.zeros((3, 3)).astype(bool)

#     stress_stack = jnp.zeros((num_steps, 3, 3))

#     material = material.create(*material_params, stress_ref=stress_ref.reshape(1, 3, 3))

#     return mix_control(material, strain_rate_stack, stress_stack, mask, volume_fraction, stress_ref, dt)