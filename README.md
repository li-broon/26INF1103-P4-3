# Project Initial Details Submission

## 1.	**Problem Statement and Target Users**

<ins>Problem Statement:</ins>

Traditional workplace incident reporting is rigid, time-consuming, and cumbersome for some users. Especially for foreign workers who have come from other countries and have to adjust to safety reporting norms that differ from one workplace to another, alongside the language barrier. 

This system solves this by letting workers report incidents conversationally in their own native languages. Then let the AI do the translating and conversing and produce a structured JSON record that is sent to a database. The AI can also extract insights from the conversation to give even more additional data for higher-ups.

<ins>Target Users:</ins>

    -	Contractors: Workers themselves who can quickly report incidents in their native language without navigating complex forms.
    -	Safety officers: They require data that is structured, categorised and accurate to ensure site safety.
    -	Supervisors & Managers: People with leadership positions who need information on work stoppages and severe safety violations.

## 2.	**User Inputs**

Users will type into the terminal similar to having a conversation with the AI. The user can provide all the information needed below. If they don’t, the system will prompt a back-and-forth conversation until the user provides all info.:

    -	Name
    -	Location
    -	Incident date and time
    -	Description of event
    -	Injury status
    -	Hospitalization status
    -	Immediate Action Taken
    -	Number of hours stopped
 
## 3.	**Use of AI**

    -	The AI will interpret any type of language input and parse all requested data points into English.
    -	Once conversation concludes, the AI will return a structured JSON response containing the necessary data.
    -	The AI itself will analyse the conversation and generate additional insightful metadata:
        -	Was it a Near-Miss
        -	Root cause categorisation
        -	Lost Time Injury
        -	AI’s severity rating
        -	AI’s safety recommendation
        -   Detected Language

## 4.	**Business Rules**

    -	Importance score: The various data points each have their own respective weights which is used to calculate each incident's importance. After calculation, the incidents are all sorted from most to least urgent, so safety officers see the most serious incidents first.
    -	Completeness check: A report is only accepted once every field is filled. If any are missing, the AI asks the worker for them in their language. If the worker cannot answer after being asked twice, the field is recorded as "unknown (worker could not say)".

    -	MOM register: every saved report that is MOM reportable is also copied into a second file, `data/mom_data.csv`, marked as "not reported yet". In the GUI, the "MOM reporting" tab lists only these reports; the safety officer ticks a report once it has been reported to MOM, and the tick (with the date) is written straight to `mom_data.csv`.

## 5.	**Repository Link:**

[https://github.com/li-broon/26INF1103-P4-3](https://github.com/li-broon/26INF1103-P4-3)

## Running with Docker

```bash
docker build -t inf1103-p4 .
docker run -it --rm -v "$(pwd)/data:/app/data" inf1103-p4

```
Command to run test cases in docker
```bash
docker run -it --rm inf1103-p4 pytest

```
or
```bash
docker run -it --rm inf1103-p4 pytest tests/logic_manager

```
to run only the `logic_manager` test cases (scoring, MOM rule and LogicManager), which fulfils the submission requirements.
Each manager's tests are in their own folder, so `tests/ai_manager`, `tests/data_manager` or `tests/io_manager` work the same way.

### Live translation check (optional, needs the API)

`tests/ai_manager/test_translation_live.py` reports the same incident in English, Malay, Chinese and Tamil through the real AI and compares the four reports: the structured fields (date, time, hospitalised, hours, severity, root cause, near miss, lost-time injury) must come out identical, and the free-text fields get a similarity score against the English run. The normal `pytest` run skips it, so CI and the test commands above stay offline. To run it, with your `.env` in place:
```bash
LIVE_AI_TESTS=1 pytest tests/ai_manager/test_translation_live.py -s

```
or in Docker:
```bash
docker run -it --rm --env-file .env -e LIVE_AI_TESTS=1 inf1103-p4 pytest tests/ai_manager/test_translation_live.py -s

```
`-s` prints the comparison table for each language. It makes about 8 API calls, and the AI's wording of the free-text fields can change between runs, so read the similarity scores as a guide rather than a pass mark.

## Running the GUI with Docker

The GUI (`python main.py --gui`) opens a window, so the container must be given your screen. Pick the command for your system (build the image first, as above).

**Linux** (X11, or Wayland with XWayland)
```bash
xhost +local:
docker run -it --rm -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix -v "$(pwd)/data:/app/data" inf1103-p4 python main.py --gui
```

**Windows: WSL terminal** (Windows 11, or Windows 10 with WSLg)
```bash
docker run -it --rm -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix -v "$(pwd)/data:/app/data" inf1103-p4 python main.py --gui
```

**Windows: PowerShell** (Windows 11 with Docker Desktop on the WSL 2 backend)
```powershell
docker run -it --rm -e DISPLAY=:0 -v /run/desktop/mnt/host/wslg/.X11-unix:/tmp/.X11-unix -v "${PWD}/data:/app/data" inf1103-p4 python main.py --gui
```

**macOS** (Intel or Apple Silicon)
1. Install [XQuartz](https://www.xquartz.org) and log out and back in.
2. Open XQuartz, go to **Settings → Security** and tick **Allow connections from network clients**, then quit and reopen XQuartz.
3. In a terminal:
```bash
xhost +localhost
docker run -it --rm -e DISPLAY=host.docker.internal:0 -v "$(pwd)/data:/app/data" inf1103-p4 python main.py --gui
```

The same `DISPLAY=host.docker.internal:0` command also works on any Windows version if an X server such as VcXsrv is running (with access control disabled).

