import dts
import emsl
import ess_dive
import jdp
import nmdc


class Client:
    def __init__(self): ...

    def query(self, SRR: str) -> dict[str, list[any]]:
        jdp_results = [r for r in jdp.Query().filter(SRR=SRR)]

        # grab metadata.gold_data.gold_stamp_id from jdp_results
        gold_id = jdp_results[0]["files"][0]["metadata"]["gold_data"]["gold_stamp_id"]
        print(gold_id)

        nmdc_results = list(
            nmdc.DataGenerationSearch().filter(
                gold_sequencing_project_identifiers=gold_id
            )
        )

        return {
            "jdp": jdp_results,
            "nmdc": nmdc_results,
        }
