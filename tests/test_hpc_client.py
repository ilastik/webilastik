import aiohttp
import asyncio
import pprint

from webilastik.libebrains.job import JobDescription, JobProxyClient, JobResources, Memory, SiteName
from webilastik.libebrains.user_token import UserToken

async def test_hpc_client():
    http_client = aiohttp.ClientSession()
    job_client = JobProxyClient(http_client_session=http_client)
    job_submission = await job_client.start_job(
        site=SiteName.DAINT_CSCS,
        service_account_token=UserToken.get_global_token_or_raise(),
        job_def=JobDescription(
            Name="my_test_job",
            Project="ich005",
            Executable="echo",
            Arguments=("some_test_string",),
            Resources=JobResources(
                Memory=Memory(1, "G")
            )
        )
    )

    pprint.pprint(job_submission)
    await http_client.close()


if __name__ == "__main__":
    asyncio.run(test_hpc_client())