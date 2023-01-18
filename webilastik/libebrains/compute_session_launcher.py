#pyright: strict

from abc import abstractmethod
import asyncio
from subprocess import Popen
from typing import Dict, Iterable, Literal, NewType, List, Set, Tuple
import uuid
import datetime
import textwrap
import tempfile
import json
from pathlib import Path
import getpass
import sys
import os

from ndstructs.utils.json_serializable import ensureJsonObject, ensureJsonString
from cryptography.fernet import Fernet
from webilastik.config import WorkflowConfig

from webilastik.libebrains.oidc_client import OidcClient
from webilastik.libebrains.user_info import UserInfo
from webilastik.libebrains.user_token import UserToken
from webilastik.server.rpc.dto import ComputeSessionDto
from webilastik.utility import ComputeNodes, Hostname, Minutes, NodeSeconds, Seconds, Username
from webilastik.utility.url import Url

ComputeSessionState = Literal[
    "BOOT_FAIL",
    "CANCELLED",
    "COMPLETED",
    "DEADLINE",
    "FAILED",
    "NODE_FAIL",
    "OUT_OF_MEMORY",
    "PENDING",
    "PREEMPTED",
    "RUNNING",
    "REQUEUED",
    "RESIZING",
    "REVOKED",
    "SUSPENDED",
    "TIMEOUT",
]

COMPUTE_SESSION_STATES: Set[ComputeSessionState] = set([
    "BOOT_FAIL",
    "CANCELLED",
    "COMPLETED",
    "DEADLINE",
    "FAILED",
    "NODE_FAIL",
    "OUT_OF_MEMORY",
    "PENDING",
    "PREEMPTED",
    "RUNNING",
    "REQUEUED",
    "RESIZING",
    "REVOKED",
    "SUSPENDED",
    "TIMEOUT",
])

FAILED_STATES: Set[ComputeSessionState] = set([
    "BOOT_FAIL",
    "CANCELLED",
    "DEADLINE",
    "FAILED",
    "NODE_FAIL",
    "OUT_OF_MEMORY",
    "PREEMPTED",
    "REVOKED",
    "TIMEOUT",
])

DONE_STATES: Set[ComputeSessionState] = set(["COMPLETED", *FAILED_STATES])

RUNNABLE_STATES: Set[ComputeSessionState] = set([
    "PENDING",
    "RUNNING",
    "REQUEUED",
    "RESIZING",
    "SUSPENDED",
])

NativeComputeSessionId = NewType("NativeComputeSessionId", int)

class ComputeSession:
    SACCT_FORMAT_ITEMS = ["JobID", "JobName", "State", "ElapsedRaw", "TimelimitRaw", "Start", "AllocNodes"]

    @classmethod
    def try_from_parsable2_raw_slurm_job_data(cls, parsable2_raw_job_data: str, fernet: Fernet) -> "ComputeSession | None | Exception":
        items = parsable2_raw_job_data.split("|")
        try:
            raw_id, job_name, raw_state, raw_elapsed, raw_time_limit, raw_start_time_utc_sec, raw_alloc_nodes = items
        except Exception as e:
            return Exception(f"Bad number of raw job parameters: {e}")

        # discard old jobs for now
        if job_name.startswith("EBRAINS"):
            return None

        try:
            metadata_json = fernet.decrypt(job_name.encode('utf8'))
        except Exception as e:
            return None
        try:
            metadata = json.loads(metadata_json)
        except Exception as e:
            return Exception(f"Could not interpret metadata comment as json: {metadata_json}")

        try:
            metadata_obj = ensureJsonObject(metadata)
            user_id = uuid.UUID(ensureJsonString(metadata_obj.get("uid")))
            compute_session_id = uuid.UUID(ensureJsonString(metadata_obj.get("sid")))
        except Exception as e:
            return Exception(f"Bad metadata json: {metadata_json}")

        clean_raw_state = raw_state.split(" ")[0]
        if clean_raw_state not in COMPUTE_SESSION_STATES:
            return Exception(f"Bad job state: '{clean_raw_state}' derived from '{raw_state}'")

        start_time_utc_sec = None if raw_start_time_utc_sec == "Unknown" else Seconds.try_from_str(raw_start_time_utc_sec)
        if isinstance(start_time_utc_sec, Exception):
            return Exception(f"Bad job start time: {raw_start_time_utc_sec}")

        time_limit_minutes = Minutes.try_from_str(raw_time_limit)
        if isinstance(time_limit_minutes, Exception):
            return Exception(f"Bad job time limit: {raw_time_limit}")

        num_nodes = ComputeNodes.try_from_str(raw_alloc_nodes)
        if isinstance(num_nodes, Exception):
            return Exception(f"Caould not parse numbe rof allocated compute nodes for job: {raw_alloc_nodes}")

        return ComputeSession(
            native_compute_session_id=NativeComputeSessionId(int(raw_id)),
            state=clean_raw_state,
            start_time_utc_sec=start_time_utc_sec,
            time_elapsed_sec=Seconds(int(raw_elapsed)),
            time_limit_minutes=time_limit_minutes,
            num_nodes=num_nodes,
            user_id=user_id,
            compute_session_id=compute_session_id,
        )

    @classmethod
    def make_session_name(
        cls, *, user_id: uuid.UUID, compute_session_id: uuid.UUID, fernet: Fernet
    ) -> str:
        comment_data = {
            "uid": str(user_id),
            "sid": str(compute_session_id),
        }
        return fernet.encrypt(
            json.dumps(comment_data, separators=(',', ':')).encode('utf8'),
        ).decode('utf8')

    def __init__(
        self,
        *,
        native_compute_session_id: NativeComputeSessionId,
        state: ComputeSessionState,
        start_time_utc_sec: "Seconds | None",
        time_elapsed_sec: Seconds,
        time_limit_minutes: Minutes,
        num_nodes: ComputeNodes,
        user_id: uuid.UUID,
        compute_session_id: uuid.UUID,
    ) -> None:
        self.native_compute_session_id = native_compute_session_id
        self.state: ComputeSessionState = state
        self.start_time_utc_sec = start_time_utc_sec
        self.time_elapsed_sec = time_elapsed_sec
        self.time_limit_minutes = time_limit_minutes
        self.num_nodes = num_nodes
        self.user_id = user_id
        self.compute_session_id = compute_session_id
        super().__init__()


    def to_dto(self) -> ComputeSessionDto:
        return ComputeSessionDto(
            start_time_utc_sec=self.start_time_utc_sec and self.start_time_utc_sec.to_int(),
            time_elapsed_sec=self.time_elapsed_sec.to_int(),
            time_limit_minutes=self.time_limit_minutes.to_int(),
            num_nodes=self.num_nodes.to_int(),
            compute_session_id=str(self.compute_session_id),
            state=self.state,
        )

    def is_running(self) -> bool:
        return self.state == "RUNNING"

    def is_runnable(self) -> bool:
        return self.state in RUNNABLE_STATES

    def has_failed(self) -> bool:
        return self.state in FAILED_STATES

    def is_done(self) -> bool:
        return self.state in DONE_STATES

    def belongs_to(self, user_info: UserInfo) -> bool:
        return self.user_id == user_info.sub

    @classmethod
    def compute_used_quota(cls, compute_sessions: Iterable["ComputeSession"]) -> NodeSeconds:
        out: NodeSeconds = NodeSeconds(0)
        for s in compute_sessions:
            out += s.time_elapsed_sec * s.num_nodes
        return out

class SshJobLauncher:
    JOB_NAME_PREFIX = "EBRAINS"

    def __init__(
        self,
        *,
        user: Username,
        hostname: Hostname,
        login_node_info: "Tuple[Username, Hostname] | None" = None,
        account: str,
        fernet: Fernet,
    ) -> None:
        self.user = user
        self.hostname = hostname
        self.account = account
        self.fernet = fernet
        self.login_node_info = login_node_info

        super().__init__()

    @classmethod
    def make_session_name(cls, user_id: uuid.UUID) -> str:
        return f"{cls.JOB_NAME_PREFIX}-{user_id}"

    async def do_ssh(
        self,
        *,
        command: str,
        command_args: List[str],
        environment: "Dict[str, str] | None" = None,
        stdin: "str | None" = None,
    ) -> "str | Exception":
        environment_preamble = ""
        if environment:
            environment_preamble = " ".join([f"{key}={value}" for key, value in environment.items()])

        login_node_preamble: List[str] = []
        if self.login_node_info:
            login_node_preamble = [
                "ssh", "-oCheckHostIP=no", "-oBatchMode=yes", f"{self.login_node_info[0]}@{self.login_node_info[1]}",
            ]

        if stdin:
            stdin_file = tempfile.TemporaryFile()
            stdin_contents = stdin.encode('utf8')
            num_bytes_written = stdin_file.write(stdin_contents)
            if num_bytes_written != len(stdin_contents):
                return Exception(f"Could not write sbatch script to temp file")
            _ = stdin_file.seek(0)
        else:
            stdin_file = None

        try:
            process = await asyncio.create_subprocess_exec(
                *login_node_preamble,
                "ssh", "-v", "-oBatchMode=yes", f"{self.user}@{self.hostname}",
                "--",
                f"{environment_preamble} {command} " + " ".join(command_args),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=stdin_file,
            )
            stdout, stderr = await process.communicate()
        except Exception as e:
            return e

        if process.returncode != 0:
            return Exception(stderr.decode())

        return stdout.decode()


    @abstractmethod
    def get_sbatch_launch_script(
        self,
        *,
        compute_session_id: uuid.UUID,
        allow_local_fs: bool,
        ebrains_oidc_client: OidcClient,
        ebrains_user_token: UserToken,
        max_duration_minutes: Minutes,
        session_url: Url,
        session_allocator_host: Hostname,
        session_allocator_username: Username,
        session_allocator_socket_path: Path
    ) -> "str":
        pass

    async def launch(
        self,
        *,
        user_id: uuid.UUID,
        compute_session_id: uuid.UUID,
        allow_local_fs: bool,
        ebrains_oidc_client: OidcClient,
        ebrains_user_token: UserToken,
        max_duration_minutes: Minutes,
        session_url: Url,
        session_allocator_host: Hostname,
        session_allocator_username: Username,
        session_allocator_socket_path: Path
    ) -> "ComputeSession | Exception":
        output_result = await self.do_ssh(
            command="sbatch",
            command_args=[
                f"--job-name={ComputeSession.make_session_name(user_id=user_id, compute_session_id=compute_session_id, fernet=self.fernet)}",
                f"--time={max_duration_minutes.to_int()}",
                f"--account={self.account}",
            ],
            stdin=self.get_sbatch_launch_script(
                compute_session_id=compute_session_id,
                allow_local_fs=allow_local_fs,
                ebrains_oidc_client=ebrains_oidc_client,
                ebrains_user_token=ebrains_user_token,
                max_duration_minutes=max_duration_minutes,
                session_url=session_url,
                session_allocator_host=session_allocator_host,
                session_allocator_username=session_allocator_username,
                session_allocator_socket_path=session_allocator_socket_path,
            ),
        )
        if isinstance(output_result, Exception):
            return output_result

        native_compute_session_id = NativeComputeSessionId(int(output_result.split()[3]))

        for _ in range(5):
            await asyncio.sleep(0.7)
            job = await self.get_compute_session_by_native_id(native_compute_session_id=native_compute_session_id)
            if isinstance(job, (Exception, ComputeSession)):
                return job
        return Exception(f"Could not retrieve job with id {native_compute_session_id}")


    async def cancel(self, compute_session: ComputeSession) -> "Exception | None":
        result = await self.do_ssh(command="scancel", command_args=[str(compute_session.native_compute_session_id)])
        if isinstance(result, Exception):
            return result
        return None

    async def get_current_compute_session_for_user(self, user_info: UserInfo) -> "ComputeSession | None | Exception":
        runnable_compute_sessions = await self.get_compute_sessions(state=RUNNABLE_STATES)
        if isinstance(runnable_compute_sessions, Exception):
            return runnable_compute_sessions
        for session in runnable_compute_sessions:
            if session.belongs_to(user_info=user_info):
                return session
        return None

    async def get_compute_session_by_native_id(self, native_compute_session_id: NativeComputeSessionId) -> "ComputeSession | None | Exception":
        compe_sessions = await self.get_compute_sessions(native_compute_session_id=native_compute_session_id)
        if isinstance(compe_sessions, Exception):
            return compe_sessions
        if len(compe_sessions) == 0:
            return None
        return compe_sessions[0]

    async def get_compute_session_by_id(self, compute_session_id: uuid.UUID, user_id: uuid.UUID) -> "ComputeSession | None | Exception":
        compute_sessions_result = await self.get_compute_sessions(user_id=user_id)
        if isinstance(compute_sessions_result, Exception):
            return compute_sessions_result
        for session in compute_sessions_result:
            if session.compute_session_id == compute_session_id:
                return session
        return None

    async def get_compute_sessions(
        self,
        *,
        native_compute_session_id: "NativeComputeSessionId | None" = None,
        state: "Set[ComputeSessionState] | None" = None,
        starttime: "datetime.datetime" = datetime.datetime(year=2020, month=1, day=1),
        endtime: "datetime.datetime | None" = None,
        user_id: "uuid.UUID | None" = None,
        compute_session_id: "uuid.UUID | None" = None,
    ) -> "List[ComputeSession] | Exception":
        endtime = endtime or datetime.datetime.today() + datetime.timedelta(days=2) # definetely in the future
        sacct_params = [
            "--allocations", # don't show individual steps
            "--noheader",
            "--parsable2", #items separated with '|'. No trailing '|'
            f"--format={','.join(ComputeSession.SACCT_FORMAT_ITEMS)}",
            f"--starttime={starttime.year:04d}-{starttime.month:02d}-{starttime.day:02d}",
            f"--endtime={endtime.year:04d}-{endtime.month:02d}-{endtime.day:02d}",
            f"--user={self.user}",
            f"--account={self.account}",
        ]

        if native_compute_session_id is not None:
            sacct_params.append(f"--jobs={native_compute_session_id}")
        if state != None and len(state) > 0:
            sacct_params.append(f"--state={','.join(state)}")

        output_result = await self.do_ssh(
            environment={"SLURM_TIME_FORMAT": r"%s"},
            command="sacct",
            command_args=sacct_params
        )
        if isinstance(output_result, Exception):
            return output_result
        jobs: List[ComputeSession] = []
        for line in output_result.split("\n")[:-1]: #skip empty newline
            job_result = ComputeSession.try_from_parsable2_raw_slurm_job_data(line, fernet=self.fernet)
            if isinstance(job_result, Exception):
                return job_result
            if job_result is None:
                continue
            if user_id and job_result.user_id != user_id:
                continue
            if compute_session_id and job_result.compute_session_id == compute_session_id:
                return [job_result]
            jobs.append(job_result)
        return jobs

class LocalJobLauncher(SshJobLauncher):
    def __init__(
        self,
        *,
        executor_getter: Literal["dask", "default"] = "default",
        user: Username = Username(getpass.getuser()),
        fernet: Fernet,
    ) -> None:
        super().__init__(
            user=user,
            hostname=Hostname("localhost"),
            account="dummy",
            fernet=fernet,
        )
        self.sessions: Dict[NativeComputeSessionId, Tuple[ComputeSession, Popen[bytes]]] = {}
        self.executor_getter = executor_getter

    def get_sbatch_launch_script(
        self,
        *,
        compute_session_id: uuid.UUID,
        allow_local_fs: bool,
        ebrains_oidc_client: OidcClient,
        ebrains_user_token: UserToken,
        max_duration_minutes: Minutes,
        session_url: Url,
        session_allocator_host: Hostname,
        session_allocator_username: Username,
        session_allocator_socket_path: Path
    ) -> str:
        working_dir = Path(f"/tmp/{compute_session_id}")
        job_config = WorkflowConfig(
            allow_local_fs=allow_local_fs,
            ebrains_oidc_client=ebrains_oidc_client,
            ebrains_user_token=ebrains_user_token,
            max_duration_minutes=max_duration_minutes,
            listen_socket=working_dir / "to-master.sock",
            session_url=session_url,
            session_allocator_host=session_allocator_host,
            session_allocator_username=session_allocator_username,
            session_allocator_socket_path=session_allocator_socket_path,
        )
        webilastik_source_dir = Path(__file__).parent.parent.parent
        redis_pid_file = f"{working_dir}/redis.pid"
        redis_unix_socket_path = f"{working_dir}/redis.sock"
        conda_env_dir = Path(os.path.realpath(sys.executable)).parent.parent

        out = textwrap.dedent(textwrap.indent(f"""
            #!/bin/bash -l

            {job_config.to_bash_exports()}

            set -xeu
            set -o pipefail

            mkdir {working_dir}
            cd {working_dir}

            # prevent numpy from spawning its own threads
            export OPENBLAS_NUM_THREADS=1
            export MKL_NUM_THREADS=1

            test -x {conda_env_dir}/bin/redis-server
            {conda_env_dir}/bin/redis-server \\
                --pidfile {redis_pid_file} \\
                --unixsocket {redis_unix_socket_path} \\
                --unixsocketperm 777 \\
                --port 0 \\
                --daemonize no \\
                --maxmemory-policy allkeys-lru \\
                --maxmemory 10gb \\
                --appendonly no \\
                --save "" \\
                --dir {working_dir} \\
                &

            NUM_TRIES=10;
            while [ ! -e {redis_pid_file} -a $NUM_TRIES -gt 0 ]; do
                echo "Redis not ready yet. Sleeping..."
                NUM_TRIES=$(expr $NUM_TRIES - 1)
                sleep 1
            done

            if [ $NUM_TRIES -eq 0 ]; then
                echo "Could not start redis"
                exit 1
            fi

            PYTHONPATH="{webilastik_source_dir}"
            PYTHONPATH+=":{webilastik_source_dir}/ndstructs/"
            PYTHONPATH+=":{webilastik_source_dir}/executor_getters/{self.executor_getter}/"
            PYTHONPATH+=":{webilastik_source_dir}/caching/redis_cache/"

            export PYTHONPATH
            export REDIS_UNIX_SOCKET_PATH="{redis_unix_socket_path}"

            {conda_env_dir / "bin/mpiexec -n 4" if self.executor_getter == "dask" else ""} "{conda_env_dir}/bin/python" {webilastik_source_dir}/webilastik/ui/workflow/ws_pixel_classification_workflow.py

            kill -2 $(cat {redis_pid_file})
            sleep 2
        """, prefix="            ", predicate=lambda line: line[0] != " "))
        # print(out)
        return out

    async def launch(
        self,
        *,
        user_id: uuid.UUID,
        compute_session_id: uuid.UUID,
        allow_local_fs: bool,
        ebrains_oidc_client: OidcClient,
        ebrains_user_token: UserToken,
        max_duration_minutes: Minutes,
        session_url: Url,
        session_allocator_host: Hostname,
        session_allocator_username: Username,
        session_allocator_socket_path: Path
    ) -> "ComputeSession | Exception":
        stdin_file = tempfile.TemporaryFile()
        _ = stdin_file.write(
            self.get_sbatch_launch_script(
                compute_session_id=compute_session_id,
                allow_local_fs=allow_local_fs,
                ebrains_oidc_client=ebrains_oidc_client,
                ebrains_user_token=ebrains_user_token,
                max_duration_minutes=max_duration_minutes,
                session_url=session_url,
                session_allocator_host=session_allocator_host,
                session_allocator_username=session_allocator_username,
                session_allocator_socket_path=session_allocator_socket_path,
            ).encode("utf8")
        )
        _ = stdin_file.seek(0)

        session_process = Popen(["bash"], stdin=stdin_file, start_new_session=True)
        native_compute_session_id = NativeComputeSessionId(len(self.sessions))
        dummy_session = ComputeSession(
            native_compute_session_id=native_compute_session_id,
            state="RUNNING",
            start_time_utc_sec=Seconds(int(datetime.datetime.now(datetime.timezone.utc).timestamp())),
            time_elapsed_sec=Seconds(1),
            num_nodes=ComputeNodes(1), #FIXME
            compute_session_id=compute_session_id,
            time_limit_minutes=max_duration_minutes,
            user_id=user_id,
        )
        self.sessions[native_compute_session_id] = (dummy_session, session_process)

        return dummy_session

    async def cancel(self, compute_session: ComputeSession) -> "Exception | None":
        self.sessions[compute_session.native_compute_session_id][1].kill()
        self.sessions[compute_session.native_compute_session_id][0].state = "CANCELLED"
        return None

    async def get_compute_sessions(
        self,
        *,
        native_compute_session_id: "NativeComputeSessionId | None" = None,
        state: "Set[ComputeSessionState] | None" = None,
        starttime: "datetime.datetime" = datetime.datetime(year=2020, month=1, day=1),
        endtime: "datetime.datetime | None" = None,
        user_id: "uuid.UUID | None" = None,
        compute_session_id: "uuid.UUID | None" = None,
    ) -> "List[ComputeSession] | Exception":
        compute_sessions: List[ComputeSession] = []
        for native_session_id, (compute_session, process) in self.sessions.items():
            if not compute_session.state in DONE_STATES:
                return_code = process.poll()
                if return_code is not None:
                    compute_session.state = "COMPLETED" if return_code == 0 else "FAILED"

            if native_compute_session_id and native_compute_session_id == native_session_id:
                return [compute_session]
            if compute_session_id and compute_session.compute_session_id == compute_session_id:
                return [compute_session]
            if user_id and compute_session.user_id != user_id:
                continue
            if state and compute_session.state not in state:
                continue
            if compute_session.start_time_utc_sec and compute_session.start_time_utc_sec.to_float() < starttime.timestamp(): #FIXME: use datetime instead of Seconds
                continue
            #FIXME: endtime?
            compute_sessions.append(compute_session)
        return compute_sessions


class JusufSshJobLauncher(SshJobLauncher):
    def __init__(self, fernet: Fernet) -> None:
        super().__init__(
            user=Username("webilastik"),
            hostname=Hostname("jusuf.fz-juelich.de"),
            account="icei-hbp-2022-0010",
            fernet=fernet,
        )

    def get_sbatch_launch_script(
        self,
        *,
        compute_session_id: uuid.UUID,
        allow_local_fs: bool,
        ebrains_oidc_client: OidcClient,
        ebrains_user_token: UserToken,
        max_duration_minutes: Minutes,
        session_url: Url,
        session_allocator_host: Hostname,
        session_allocator_username: Username,
        session_allocator_socket_path: Path
    ) -> str:
        working_dir = Path(f"$SCRATCH/{compute_session_id}")
        job_config = WorkflowConfig(
            allow_local_fs=allow_local_fs,
            ebrains_oidc_client=ebrains_oidc_client,
            ebrains_user_token=ebrains_user_token,
            max_duration_minutes=max_duration_minutes,
            listen_socket=working_dir / "to-master.sock",
            session_url=session_url,
            session_allocator_host=session_allocator_host,
            session_allocator_username=session_allocator_username,
            session_allocator_socket_path=session_allocator_socket_path,
        )
        home="/p/home/jusers/webilastik/jusuf"
        webilastik_source_dir = f"{working_dir}/webilastik"
        conda_env_dir = f"{home}/miniconda3/envs/webilastik"
        redis_pid_file = f"{working_dir}/redis.pid"
        redis_unix_socket_path = f"{working_dir}/redis.sock"

        out = textwrap.dedent(textwrap.indent(f"""\
            #!/bin/bash -l
            #SBATCH --nodes=1
            #SBATCH --ntasks=2
            #SBATCH --partition=batch
            #SBATCH --hint=nomultithread

            jutil env activate -p {self.account}
            {job_config.to_bash_exports()}

            set -xeu
            set -o pipefail

            module load git
            module load GCC/11.2.0
            module load OpenMPI/4.1.2

            mkdir {working_dir}
            cd {working_dir}
            # FIXME: download from github when possible
            git clone --depth 1 --branch master {home}/webilastik.git {webilastik_source_dir}

            # prevent numpy from spawning its own threads
            export OPENBLAS_NUM_THREADS=1
            export MKL_NUM_THREADS=1

            test -x {conda_env_dir}/bin/redis-server
            srun -n 1 --overlap -u --cpu_bind=none --cpus-per-task 6 \\
                {conda_env_dir}/bin/redis-server \\
                --pidfile {redis_pid_file} \\
                --unixsocket {redis_unix_socket_path} \\
                --unixsocketperm 777 \\
                --port 0 \\
                --daemonize no \\
                --maxmemory-policy allkeys-lru \\
                --maxmemory 100gb \\
                --appendonly no \\
                --save "" \\
                --dir {working_dir} \\
                &

            NUM_TRIES=10;
            while [ ! -e {redis_pid_file} -a $NUM_TRIES -gt 0 ]; do
                echo "Redis not ready yet. Sleeping..."
                NUM_TRIES=$(expr $NUM_TRIES - 1)
                sleep 1
            done

            if [ $NUM_TRIES -eq 0 ]; then
                echo "Could not start redis"
                exit 1
            fi

            PYTHONPATH="{webilastik_source_dir}"
            PYTHONPATH+=":{webilastik_source_dir}/executor_getters/jusuf/"
            PYTHONPATH+=":{webilastik_source_dir}/caching/redis_cache/"

            export PYTHONPATH
            export REDIS_UNIX_SOCKET_PATH="{redis_unix_socket_path}"

            srun -n 1 --overlap -u --cpus-per-task 120 \\
                "{conda_env_dir}/bin/python" {webilastik_source_dir}/webilastik/ui/workflow/ws_pixel_classification_workflow.py \\

            kill -2 $(cat {redis_pid_file}) #FXME: this only works because it's a single node
            sleep 2
        """, prefix="            ", predicate=lambda line: line[0] != " "))
        # print(out)
        return out

class CscsSshJobLauncher(SshJobLauncher):
    def __init__(self, fernet: Fernet):
        super().__init__(
            user=Username("bp000188"),
            hostname=Hostname("daint.cscs.ch"),
            login_node_info=(Username("bp000188"), Hostname("ela.cscs.ch")),
            account="ich005",
            fernet=fernet,
        )

    def get_sbatch_launch_script(
        self,
        *,
        compute_session_id: uuid.UUID,
        allow_local_fs: bool,
        ebrains_oidc_client: OidcClient,
        ebrains_user_token: UserToken,
        max_duration_minutes: Minutes,
        session_url: Url,
        session_allocator_host: Hostname,
        session_allocator_username: Username,
        session_allocator_socket_path: Path
    ) -> str:
        working_dir = Path(f"$SCRATCH/{compute_session_id}")
        job_config = WorkflowConfig(
            allow_local_fs=allow_local_fs,
            ebrains_oidc_client=ebrains_oidc_client,
            ebrains_user_token=ebrains_user_token,
            max_duration_minutes=max_duration_minutes,
            listen_socket=working_dir / "to-master.sock",
            session_url=session_url,
            session_allocator_host=session_allocator_host,
            session_allocator_username=session_allocator_username,
            session_allocator_socket_path=session_allocator_socket_path,
        )
        home=f"/users/{self.user}"
        webilastik_source_dir = f"{working_dir}/webilastik"
        conda_env_dir = f"{home}/miniconda3/envs/webilastik"
        redis_pid_file = f"{working_dir}/redis.pid"
        redis_port = "6379"
        num_nodes = 10

        out =  textwrap.dedent(textwrap.indent(f"""\
            #!/bin/bash
            #SBATCH --nodes={num_nodes}
            #SBATCH --ntasks-per-node=2
            #SBATCH --partition=normal
            #SBATCH --hint=nomultithread
            #SBATCH --constraint=mc

            {job_config.to_bash_exports()}

            set -xeu
            set -o pipefail

            mkdir {working_dir}
            cd {working_dir}
            git clone --depth 1 --branch master {home}/source/webilastik {webilastik_source_dir}

            # prevent numpy from spawning its own threads
            export OPENBLAS_NUM_THREADS=1
            export MKL_NUM_THREADS=1

            REDIS_IP=$(ip -o addr show ipogif0 | grep -E '\\binet\\b' | awk '{{print $4}}' | cut -d/ -f1)

            test -x {conda_env_dir}/bin/redis-server
            srun --nodes=1-1 --ntasks 1 -u --cpu_bind=none \\
                {conda_env_dir}/bin/redis-server \\
                --pidfile {redis_pid_file} \\
                --bind $REDIS_IP \\
                --port {redis_port} \\
                --daemonize no \\
                --maxmemory-policy allkeys-lru \\
                --maxmemory 48gb \\
                --appendonly no \\
                --save "" \\
                --dir {working_dir} \\
                &

            NUM_TRIES=10;
            while [ ! -e {redis_pid_file} -a $NUM_TRIES -gt 0 ]; do
                echo "Redis not ready yet. Sleeping..."
                NUM_TRIES=$(expr $NUM_TRIES - 1)
                sleep 1
            done

            if [ $NUM_TRIES -eq 0 ]; then
                echo "Could not start redis"
                exit 1
            fi

            PYTHONPATH="{webilastik_source_dir}"
            PYTHONPATH+=":{webilastik_source_dir}/executor_getters/cscs/"
            PYTHONPATH+=":{webilastik_source_dir}/caching/redis_cache/"

            export PYTHONPATH
            export REDIS_HOST_PORT="$REDIS_IP:{redis_port}"

            srun -N {num_nodes - 1} \\
                "{conda_env_dir}/bin/python" {webilastik_source_dir}/webilastik/ui/workflow/ws_pixel_classification_workflow.py \\

            kill -2 $(cat {redis_pid_file})
            sleep 2
        """, prefix="            ", predicate=lambda line: line[0] != " "))
        # print(out)
        return out