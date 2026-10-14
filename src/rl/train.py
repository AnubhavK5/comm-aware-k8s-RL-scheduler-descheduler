"""Training script for PPO Descheduling Agent using Stable-Baselines3."""

import os
import logging
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.evaluation import evaluate_policy

from src.rl.env.cluster_env import K8sClusterEnv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RLTrainer")

def train():
    os.makedirs("src/rl/models", exist_ok=True)
    model_path = "src/rl/models/ppo_descheduler.zip"

    logger.info("Initializing K8sClusterEnv Gymnasium environment...")
    env = K8sClusterEnv(
        num_nodes=3,
        num_pods=12,
        max_steps=40,
        resource_weight=0.5,
        comm_weight=0.5,
        eviction_cost=0.3
    )

    logger.info("Creating PPO model with MlpPolicy...")
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=3e-4,
        n_steps=256,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        verbose=1,
    )

    total_timesteps = 25000
    logger.info(f"Training PPO descheduler for {total_timesteps} timesteps...")
    model.learn(total_timesteps=total_timesteps)

    logger.info(f"Saving trained model to {model_path}...")
    model.save(model_path)

    # Evaluate the trained policy
    logger.info("Evaluating trained policy...")
    mean_reward, std_reward = evaluate_policy(model, env, n_eval_episodes=20)
    logger.info(f"Evaluation over 20 episodes: Mean Reward = {mean_reward:.4f} +/- {std_reward:.4f}")

    return model_path

if __name__ == "__main__":
    train()
