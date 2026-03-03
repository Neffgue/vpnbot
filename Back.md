ssh1 neffgue313       
neffgue313@ssh1's password: 
Linux ssh1 6.12.49-alwaysdata #1 SMP PREEMPT_DYNAMIC Mon Sep 29 14:04:11 UTC 2025 x86_64

  * Any process using too much CPU, RAM or IO will get killed
  * Any process running for too long (e.g. days) will get killed
  * If you want to have cron jobs, use scheduled tasks: https://help.alwaysdata.com/en/tasks/
  * If you want to have processes running 24/7, use services: https://help.alwaysdata.com/en/services/

Last login: Mon Mar  2 22:36:00 2026 from 2a00:b6e0:1:50:2::1
neffgue313@ssh1:~$ cd ~/vpnbot && git pull origin master && ~/vpnbot/venv/bin/pip install aiogram aiohttp --upgrade && 
~/vpnbot/venv/bin/python -c "import aiogram; print('OK:', aiogram.__version__)"
Username for 'https://github.com': Neffgue
Password for 'https://Neffgue@github.com': 
From https://github.com/Neffgue/vpnbot
 * branch            master     -> FETCH_HEAD
Already up to date.
Requirement already satisfied: aiogram in ./venv/lib/python3.11/site-packages (3.25.0)
Requirement already satisfied: aiohttp in ./venv/lib/python3.11/site-packages (3.10.11)
Collecting aiohttp
  Downloading aiohttp-3.13.3-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (8.1 kB)
Requirement already satisfied: aiofiles<26.0,>=23.2.1 in ./venv/lib/python3.11/site-packages (from aiogram) (25.1.0)
Requirement already satisfied: certifi>=2023.7.22 in ./venv/lib/python3.11/site-packages (from aiogram) (2026.2.25)
Requirement already satisfied: magic-filter<1.1,>=1.0.12 in ./venv/lib/python3.11/site-packages (from aiogram) (1.0.12)
Requirement already satisfied: pydantic<2.13,>=2.4.1 in ./venv/lib/python3.11/site-packages (from aiogram) (2.10.4)
Requirement already satisfied: typing-extensions<=5.0,>=4.7.0 in ./venv/lib/python3.11/site-packages (from aiogram) (4.15.0)
Requirement already satisfied: aiohappyeyeballs>=2.5.0 in ./venv/lib/python3.11/site-packages (from aiohttp) (2.6.1)
Requirement already satisfied: aiosignal>=1.4.0 in ./venv/lib/python3.11/site-packages (from aiohttp) (1.4.0)
Requirement already satisfied: attrs>=17.3.0 in ./venv/lib/python3.11/site-packages (from aiohttp) (25.4.0)
Requirement already satisfied: frozenlist>=1.1.1 in ./venv/lib/python3.11/site-packages (from aiohttp) (1.8.0)
Requirement already satisfied: multidict<7.0,>=4.5 in ./venv/lib/python3.11/site-packages (from aiohttp) (6.7.1)
Requirement already satisfied: propcache>=0.2.0 in ./venv/lib/python3.11/site-packages (from aiohttp) (0.4.1)
Requirement already satisfied: yarl<2.0,>=1.17.0 in ./venv/lib/python3.11/site-packages (from aiohttp) (1.23.0)
Requirement already satisfied: annotated-types>=0.6.0 in ./venv/lib/python3.11/site-packages (from pydantic<2.13,>=2.4.1->aiogram) (0.7.0)
Requirement already satisfied: pydantic-core==2.27.2 in ./venv/lib/python3.11/site-packages (from pydantic<2.13,>=2.4.1->aiogram) (2.27.2)
Requirement already satisfied: idna>=2.0 in ./venv/lib/python3.11/site-packages (from yarl<2.0,>=1.17.0->aiohttp) (3.11)
Downloading aiohttp-3.13.3-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (1.7 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.7/1.7 MB 29.3 MB/s  0:00:00
Installing collected packages: aiohttp
  Attempting uninstall: aiohttp
    Found existing installation: aiohttp 3.10.11
    Uninstalling aiohttp-3.10.11:
      Successfully uninstalled aiohttp-3.10.11
Successfully installed aiohttp-3.13.3
OK: 3.25.0
neffgue313@ssh1:~/vpnbot$