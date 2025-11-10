# main_final_qt.py
import os
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

import sys
import random
import time

# Matplotlib gunakan Qt5Agg (kamu sudah install PyQt5)
import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt

# PyQt5 untuk form input
from PyQt5 import QtWidgets, QtCore, QtGui

# Pygame untuk simulasi visual
import pygame

# -------------------------------------------------------
# Qt5 Dialog: simple form to get num_tasks and num_cores
# -------------------------------------------------------
class ParamDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Input Parameter Simulasi")
        self.setFixedSize(320, 180)

        layout = QtWidgets.QVBoxLayout()

        label = QtWidgets.QLabel("Masukkan parameter simulasi:")
        label.setStyleSheet("font-weight: bold;")
        layout.addWidget(label)

        form = QtWidgets.QFormLayout()
        self.tasks_input = QtWidgets.QLineEdit("20")
        self.tasks_input.setValidator(QtGui.QIntValidator(1, 1000, self))
        form.addRow("Jumlah task:", self.tasks_input)

        self.cores_input = QtWidgets.QLineEdit("4")
        self.cores_input.setValidator(QtGui.QIntValidator(1, 64, self))
        form.addRow("Jumlah core (Mode Parallel):", self.cores_input)

        layout.addLayout(form)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.start_btn = QtWidgets.QPushButton("Mulai Simulasi")
        self.cancel_btn = QtWidgets.QPushButton("Batal")
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.start_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Signals
        self.start_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

    def get_values(self):
        try:
            n = int(self.tasks_input.text())
        except:
            n = 20
        try:
            c = int(self.cores_input.text())
        except:
            c = 4
        return max(1, n), max(1, c)

# -------------------------------------------------------
# Simulasi: Task & Core classes + runner
# -------------------------------------------------------
class Task:
    def __init__(self, duration):
        self.duration = float(duration)  # total "work" units
        self.remaining = float(duration)
        self.done = False

    def work(self, amount):
        if not self.done:
            self.remaining -= amount
            if self.remaining <= 0:
                self.remaining = 0
                self.done = True

class CPUCore:
    def __init__(self, core_id, x, y, w=140, h=28):
        self.id = core_id
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.current_task = None
        self.queue = []

    def assign(self, task):
        self.queue.append(task)

    def update(self, work_amount):
        # if idle, pop next
        if self.current_task is None and self.queue:
            self.current_task = self.queue.pop(0)
        # work on current
        if self.current_task:
            self.current_task.work(work_amount)
            if self.current_task.done:
                self.current_task = None

    def load_count(self):
        # load = one ongoing task + length of queue
        return (1 if self.current_task else 0) + len(self.queue)

# Distribute tasks initially: give each task to least loaded core (simple dynamic balancer)
def distribute_initial(tasks, cores):
    for t in tasks:
        target = min(cores, key=lambda c: c.load_count())
        target.assign(t)

# -------------------------------------------------------
# Pygame visualization runner
# -------------------------------------------------------
def run_pygame_simulation(num_cores, num_tasks, mode_name, screen_size=(960, 560)):
    pygame.init()
    screen = pygame.display.set_mode(screen_size)
    pygame.display.set_caption(f"Simulasi - {mode_name}")
    font = pygame.font.SysFont("consolas", 18)
    clock = pygame.time.Clock()

    # create tasks with random durations (units)
    tasks = [Task(random.randint(80, 150)) for _ in range(num_tasks)]

    # create cores with positions
    cores = []
    # center horizontally; spread horizontally
    margin_x = 80
    spacing = (screen_size[0] - margin_x * 2) / max(1, num_cores)
    base_y = 200
    for i in range(num_cores):
        x = int(margin_x + i * spacing + (spacing - 140)/2)
        y = base_y
        cores.append(CPUCore(i, x, y))

    # initial distribution (dynamic)
    distribute_initial(tasks, cores)

    start_time = time.time()
    running = True
    done_count = 0
    total_tasks = len(tasks)

    # keep a flat reference to task objects to compute done_count easily
    all_tasks = tasks

    # Sim speed factor: how much "work units" per frame (scale tuned)
    SPEED_FACTOR = 0.08  # tweak this to make simulation faster/slower visually

    while running:
        dt_ms = clock.tick(60)
        dt = dt_ms / 1000.0  # seconds
        work_amount = dt_ms * SPEED_FACTOR  # work units applied this frame

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit

        # update cores
        for core in cores:
            core.update(work_amount)

        # recompute done_count
        done_count = sum(1 for t in all_tasks if t.done)
        percent = (done_count / total_tasks) * 100 if total_tasks > 0 else 100.0

        # draw background
        screen.fill((18, 18, 30))

        # Title & info
        title_surf = font.render(mode_name, True, (255, 215, 0))
        screen.blit(title_surf, (30, 22))
        info_surf = font.render(f"Tasks done: {done_count}/{total_tasks}   Progress: {percent:.1f}%", True, (220,220,220))
        screen.blit(info_surf, (30, 52))

        # draw global progress bar
        bar_x, bar_y, bar_w, bar_h = 30, 84, screen_size[0]-60, 18
        pygame.draw.rect(screen, (70,70,90), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
        pygame.draw.rect(screen, (80,200,120), (bar_x, bar_y, int(bar_w*(percent/100.0)), bar_h), border_radius=6)

        # draw cores and their progress
        for core in cores:
            # box
            pygame.draw.rect(screen, (40,40,60), (core.x, core.y, core.w, core.h), border_radius=6)
            # if active, draw progress inside box for the current task
            if core.current_task:
                ratio = 1.0 - (core.current_task.remaining / core.current_task.duration)
                pygame.draw.rect(screen, (60,160,200), (core.x, core.y, int(core.w * ratio), core.h), border_radius=6)
            # core label and queue len
            lbl = font.render(f"Core {core.id+1}  | queue:{len(core.queue)}", True, (230,230,230))
            screen.blit(lbl, (core.x, core.y - 22))

        pygame.display.flip()

        # stop condition
        if done_count >= total_tasks:
            running = False

    exec_time = time.time() - start_time
    pygame.quit()
    return exec_time

# -------------------------------------------------------
# Summary plot (Matplotlib Qt)
# -------------------------------------------------------
def show_summary_window(single_time, parallel_time):
    modes = ["Single", "Parallel"]
    times = [single_time, parallel_time]
    fig, ax = plt.subplots(figsize=(6,4))
    bars = ax.bar(modes, times, color=["#d9534f", "#5cb85c"])
    ax.set_ylabel("Execution time (s)")
    ax.set_title("Perbandingan Execution Time")
    for bar, t in zip(bars, times):
        ax.text(bar.get_x() + bar.get_width()/2, t + 0.02, f"{t:.2f}s", ha="center", va="bottom")
    plt.tight_layout()
    plt.show()  # Qt window - close manually

# -------------------------------------------------------
# Main flow: show Qt dialog -> run pygame modes -> show summary with Qt
# -------------------------------------------------------
def main():
    # Qt Application for initial dialog
    app = QtWidgets.QApplication(sys.argv)
    dlg = ParamDialog()
    result = dlg.exec_()
    if result != QtWidgets.QDialog.Accepted:
        print("User cancelled.")
        return

    num_tasks, num_cores = dlg.get_values()
    # close Qt app cleanly before launching pygame (we'll later open plot window separately)
    app.quit()

    # Mode 1: Single processing (1 core)
    print(f"[SIM] Running Mode 1 (Single) with {num_tasks} tasks...")
    single_time = run_pygame_simulation(1, num_tasks, "MODE 1: SINGLE PROCESSING")

    # after mode 1, show a small pygame info screen and wait for RIGHT arrow
    pygame.init()
    info_screen = pygame.display.set_mode((760, 140))
    pygame.display.set_caption("Mode 1 selesai")
    font = pygame.font.SysFont("consolas", 18)
    info_screen.fill((10,10,10))
    info_screen.blit(font.render(f"Mode 1 selesai. Execution time: {single_time:.2f} s", True, (220,220,220)), (20, 20))
    info_screen.blit(font.render("Tekan panah kanan (→) untuk lanjut ke Mode 2.", True, (255,215,0)), (20, 60))
    pygame.display.flip()
    wait = True
    while wait:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                return
            if e.type == pygame.KEYDOWN and e.key == pygame.K_RIGHT:
                wait = False
    pygame.display.quit()

    # Mode 2: Parallel processing with num_cores
    print(f"[SIM] Running Mode 2 (Parallel) with {num_cores} cores and {num_tasks} tasks...")
    parallel_time = run_pygame_simulation(num_cores, num_tasks, "MODE 2: PARALLEL PROCESSING + SCHEDULING")

    # after mode 2, info and wait for right arrow to show summary
    pygame.init()
    info_screen = pygame.display.set_mode((760, 140))
    pygame.display.set_caption("Mode 2 selesai")
    font = pygame.font.SysFont("consolas", 18)
    info_screen.fill((10,10,10))
    info_screen.blit(font.render(f"Mode 2 selesai. Execution time: {parallel_time:.2f} s", True, (220,220,220)), (20, 20))
    info_screen.blit(font.render("Tekan panah kanan (→) untuk melihat summary (grafik).", True, (255,215,0)), (20, 60))
    pygame.display.flip()
    wait = True
    while wait:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                return
            if e.type == pygame.KEYDOWN and e.key == pygame.K_RIGHT:
                wait = False
    pygame.display.quit()

    # Show final summary window (matplotlib + Qt)
    show_summary_window(single_time, parallel_time)

    # final pygame screen informing end, wait ESC to quit
    pygame.init()
    screen = pygame.display.set_mode((760, 120))
    pygame.display.set_caption("Simulasi selesai")
    font = pygame.font.SysFont("consolas", 18)
    screen.fill((10,10,10))
    screen.blit(font.render("Simulasi selesai. Tutup jendela grafik kemudian tekan ESC untuk keluar.", True, (255,215,0)), (20, 40))
    pygame.display.flip()
    waiting = True
    while waiting:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                waiting = False
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                waiting = False
    pygame.quit()

if __name__ == "__main__":
    main()