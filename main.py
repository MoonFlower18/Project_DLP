import psutil
import socket
import os
import time
import threading
import wmi
import subprocess
import pythoncom

# запись IP адресов
previous_ips = {}

def log_event(message):
    # вывод даты и времени события
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print(f"[{timestamp}] {message}")

def ip_to_url(ip):
    try:
        hostname, aliaslist, ipaddrlist = socket.gethostbyaddr(ip)
        return aliaslist[0] if aliaslist else hostname
    except socket.herror:
        return 'Unknown'

def get_chrome_ips():
    current_ips = {}
    chrome_processes = [process.info['pid'] for process in psutil.process_iter(attrs=['pid', 'name']) if
                        'chrome' in process.info['name'].lower()]

    for pid in chrome_processes:
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'ESTABLISHED' and conn.pid == pid:
                address = conn.raddr.ip
                url_addr = ip_to_url(address)
                current_ips[address] = url_addr
    return current_ips

def network_monitor():
    global previous_ips
    previous_ips = get_chrome_ips()
    print("=" * 100)
    log_event("Текущие IP:")
    for ip, url in previous_ips.items():
        print(f"IP: {ip} URL: {url}")

    while True:
        current_ips = get_chrome_ips()

        new_ips = {ip: url for ip, url in current_ips.items() if ip not in previous_ips}
        closed_ips = {ip: url for ip, url in previous_ips.items() if ip not in current_ips}

        if new_ips:
            print("=" * 100)
            log_event("Новые IP:")
            for ip, url in new_ips.items():
                print(f"IP: {ip} URL: {url}")

        if closed_ips:
            print("=" * 100)
            log_event("Закрытые IP:")
            for ip, url in closed_ips.items():
                print(f"IP: {ip} URL: {url}")

        previous_ips = current_ips
        time.sleep(1)

downloads_folder = 'C:\\Users\\Downloads'  # папка загрузок

def monitor_downloads():
    files_before = set(os.listdir(downloads_folder))
    while True:
        time.sleep(5)
        files_after = set(os.listdir(downloads_folder))

        new_files = {f for f in files_after - files_before if not (f.endswith('.crdownload') or f.endswith('.tmp'))}
        deleted_files = {f for f in files_before - files_after if not (f.endswith('.crdownload') or f.endswith('.tmp'))}

        if new_files:
            print("=" * 100)
            for filename in new_files:
                clean_filename = filename.replace('{', '').replace('}', '')
                log_event(f'Скачан новый файл: {clean_filename}')

        if deleted_files:
            print("=" * 100)
            for filename in deleted_files:
                clean_filename = filename.replace('{', '').replace('}', '')
                log_event(f'Удалён файл: {clean_filename}')

        files_before = files_after

# блокировка USB
def eject_device(drive_letter):
    try:
        command = f"diskpart /s eject_{drive_letter}.txt"
        with open(f"eject_{drive_letter}.txt", "w") as script_file:
            script_file.write(f"select volume {drive_letter}\n")
            script_file.write(f"remove\n")

        # выполнение команды diskpart с созданным скриптом извлечения
        subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        log_event(f"Устройство {drive_letter} успешно извлечено.")
    except Exception as e:
        log_event(f"Ошибка при извлечении устройства {drive_letter}: {e}")

def monitor_usb():
    pythoncom.CoInitialize()  # инициализация COM

    c = wmi.WMI()
    watcher = c.Win32_VolumeChangeEvent.watch_for()

    while True:
        try:
            event = watcher()
            if event.EventType == 2:  # код подключения устройства
                drive_letter = event.DriveName
                print("=" * 100)
                log_event(f"Попытка подключения съемного носителя: {drive_letter}")

                # проверка на флешку (DriveType=2)
                drives = c.Win32_LogicalDisk(DriveType=2)
                removable_drives = [d.DeviceID for d in drives]
                if drive_letter in removable_drives:
                    log_event(f"Съемный носитель обнаружен: {drive_letter}. Блокировка...")
                    eject_device(drive_letter)
        except Exception as e:
            log_event(f"Ошибка: {e}")


# многопоточность
usb_thread = threading.Thread(target=monitor_usb)
network_thread = threading.Thread(target=network_monitor)
download_thread = threading.Thread(target=monitor_downloads)

# пуск потоков
usb_thread.start()
network_thread.start()
download_thread.start()