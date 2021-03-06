import numpy as np
import scipy.linalg
import cv2
import argparse
import os
from tqdm import tqdm
import random
import math
##dynamics of this system are of the form
## x'' = -kx + ax'
##
## Reparametrize the system as p = [x, x']
## The dynamics are then
##
## p' = Ap = [0, I; -k, a]p
##
## with solution p(t) = e^(At)p(0)

## Takes in time t and initial state p0

"""
def solve_disk(t, p0, runtime_config):
  A = np.zeros((4,4))
  A[0:2,2:4] = np.eye(2)
  A[2:4,0:2] = runtime_config.spring * np.eye(2)
  A[2:4,2:4] = runtime_config.drag * np.eye(2)
  At = t*A
  exp_At = scipy.linalg.expm(At)
  exp_At = np.asmatrix(exp_At)
  p0 = np.asmatrix(p0).T
  return np.dot(exp_At, p0)
"""

def generate_expA(runtime_config):
  A = np.zeros((4,4))
  A[0:2,2:4] = np.eye(2)
  A[2:4,0:2] = runtime_config.spring * np.eye(2)
  A[2:4,2:4] = runtime_config.drag * np.eye(2)
  At = A
  exp_At = scipy.linalg.expm(At)
  exp_At = np.asmatrix(exp_At)
  return exp_At

def solve_disk(pcur, runtime_config):
  A = generate_expA(runtime_config)
  return np.dot(A, pcur)

def init_disk(r=None, c=None):
  p0 = np.random.rand(4)
  p0 -= 0.5
  p0 *= WINDOW_SIZE
  p0[2:4] = 0.0
  if r is None: r = np.random.rand(1)*12.5
  if c is None: c = np.random.rand(3)*255
  c = (int(c[0]), int(c[1]), int(c[2]))
  r = int(r)
  return p0, r, c

def draw_sol_onto_image(sol, col, img, path, rad):
  x = sol[0]
  y = sol[1]
  cv2.circle(img, (int(WINDOW_SIZE/2) + int(x), int(WINDOW_SIZE/2) + int(y)), rad, col, -1)

def init_image():
  img = np.zeros((WINDOW_SIZE, WINDOW_SIZE, 3))
  img.fill(0)
  cv2.line(img, (int(WINDOW_SIZE/2), 0), (int(WINDOW_SIZE/2), int(WINDOW_SIZE)-1), (0,0,0))
  cv2.line(img, (0, int(WINDOW_SIZE/2)), (WINDOW_SIZE-1, int(WINDOW_SIZE/2)), (0,0,0))
  return img

def draw_sols_onto_image(sols, cols, rads, path, draw=False):
  img = init_image()
  for i in range(len(sols)): 
    draw_sol_onto_image(sols[i], cols[i], img, path, rads[i])
  if draw: cv2.imwrite(path, img)
  return img

def run_disk(runtime_config, red_disk=False):
  p0, r, c= init_disk()
  if red_disk: p0, r, c = init_disk(r=5.0,c=(0,0,255))
  sols = [np.asmatrix(p0).T]
  pcur = np.asmatrix(p0).T
  for t in range(runtime_config.steps-1):
    #sol = solve_disk(t, p0, runtime_config)
    sol = solve_disk(pcur, runtime_config)
    noise = np.random.normal(runtime_config.mu, np.sqrt(runtime_config.sig2), (4,1))
    noise[0:2] = 0.0
    sol = sol + noise
    sols.append(sol)
    pcur = sol
    #draw_sols_onto_image([sol],[(0,0,255)], "./imgs/" + str(t) + ".png")
  return (sols, r, c)

def write_traj_on_image(img, traj, color):
  N = traj.shape[1]
  c = WINDOW_SIZE/2
  for i in range(N-1):
    cv2.line(img, (int(c + traj[0,i]), int(c + traj[1,i])), (int(c + traj[0,i+1]), int(c + traj[1,i+1])), color) 

def run_and_save_disks(runtime_config, number):
  n = runtime_config.n
  sol_sets = [run_disk(runtime_config) for i in range(n)]
  red_set = run_disk(runtime_config, red_disk=True)
  sol_sets.append(red_set)
  random.shuffle(sol_sets)

  ##draw images
  cols = [elem[2] for elem in sol_sets]
  rads = [elem[1] for elem in sol_sets]
  time_sols = []
  for t in range(runtime_config.steps):
    sols_t = [elem[0][t] for elem in sol_sets]
    time_sols.append(sols_t)
  imgs = []
  for t in range(runtime_config.steps): 
    img = draw_sols_onto_image(time_sols[t], cols, rads, runtime_config.dir + "/imgs/" + number + "_" + str(t) + ".png", draw=True)
    imgs.append(img)

  imgs_full = np.stack(imgs, axis=0)
  np.save(runtime_config.dir + "/redDot/" + number + "_img.npy", imgs_full)
  ##write out trajectory
  red_output = np.hstack(red_set[0])
  np.save(runtime_config.dir + "/redDot/" + number + "_pos.npy", red_output)
  traj_img = init_image()
  write_traj_on_image(traj_img, red_output, (0,0,255))
  cv2.imwrite(runtime_config.dir + '/orig_traj/' + number + '.png', traj_img)

SPRING_CONSTANT = -0.1
DRAG_CONSTANT = -1.0
DIM = 2
WINDOW_SIZE = 128 ## 256 x 256 images 
MU = 0.0
SIG2 = 200.0
N = 10
STEPS = 100
NT = 100
DIR = "./train"
class RConfig:
  def __init__(self, args):
    self.spring = args['spring_const'] if args['spring_const'] is not None else SPRING_CONSTANT
    self.drag = args['drag_const'] if args['spring_const'] is not None else DRAG_CONSTANT
    self.mu = args['mean_noise'] if args['mean_noise'] is not None else MU
    self.sig2 = args['std_noise'] if args['std_noise'] is not None else SIG2
    self.n = args['num_disks'] if args['num_disks'] is not None else N
    self.steps = args['time_steps'] if args['time_steps'] is not None else STEPS
    self.dir = args['base_dir'] if args['base_dir'] is not None else DIR

import pickle
def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--spring-const', '-k', type=float, help="Spring constant (default -5)")
  parser.add_argument('--drag-const', '-d', type=float, help="Drag constant (default -1)")
  parser.add_argument('--mean-noise', '-mu', type=float, help="Mean of Gaussian noise")
  parser.add_argument('--std-noise', '-sig2', type=float, help="var of Gaussian noise")
  parser.add_argument('--num-disks', '-n', type=int, help="Number of disks to render")
  parser.add_argument('--time-steps', '-t', type=int, help="Number of steps to sample")
  parser.add_argument('--base-dir', '-dir', type=str, help="directory for encoding")
  arg_dict = vars(parser.parse_args())
  runtime_config = RConfig(arg_dict)  
  print(runtime_config)
  print(arg_dict)
  A = generate_expA(runtime_config)
  B = np.zeros((4,2))
  B[2,0] = 1.0
  B[3,1] = 1.0
  C = np.zeros((2,4))
  C[0,0] = 1.0
  C[1,1] = 1.0
  d = {}
  d['A'] = A
  d['B'] = B
  d['C'] = C
  Q = np.eye(2) * SIG2
  d['Q'] = Q

  if not os.path.exists(runtime_config.dir + "/redDot"):
    os.makedirs(runtime_config.dir + "/redDot")
  if not os.path.exists(runtime_config.dir + "/orig_traj"):
    os.makedirs(runtime_config.dir + "/orig_traj")
  with open('./train/dynamics.pkl', 'wb') as f:
      pickle.dump(d, f)
  #return

  if not os.path.exists(runtime_config.dir + "/imgs"): 
    os.makedirs(runtime_config.dir + "/imgs")
  else:
    for files in os.listdir(runtime_config.dir + "/imgs"): os.remove(runtime_config.dir + "/imgs/" + files)
  for i in tqdm(range(NT)): run_and_save_disks(runtime_config, str(i))

if __name__ == "__main__": main()
