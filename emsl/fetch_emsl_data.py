import requests 
import json
import re

dataPortalURL = "https://sc-data-dev.emsl.pnl.gov" # Internal URL, will change to a public URL soon. 
emslProjectURL = "https://api.emsl.pnnl.gov/external/projects/"

print("Fetching project list from EMSL")

try:
    response = requests.get(dataPortalURL + "/study")
    response.raise_for_status()
except requests.exceptions.HTTPError as err:
    print(err)
    exit()

projects = response.json()
for project in projects:
    print("Fetching details for project: " + project['id'] + "...")
    try:
        response = requests.get(emslProjectURL + project['uuid'])
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(err)
        exit
    projectDetails = response.json()
    project.update(projectDetails)


print("Project details acquired.")
print("Fetching associated samples...")

def fetch_samples(dataPortalURL):
    all_samples = []
    page_number = 1
    per_page = 1000

    while True:
        try:
            url = f"{dataPortalURL}/sample?page={page_number}&per_page={per_page}"
            response = requests.get(url)
            response.raise_for_status() 
            data = response.json()

            if not isinstance(data, dict):
                print(f"Error: Unexpected API response format: {data}")
                return None

            samples = data.get("samples", [])
            all_samples.extend(samples)

            pagination = {
                "total": data.get("total"),
                "page": data.get("page"),
                "pages": data.get("pages"),
            }

            if not all(pagination.values()):
                print(f"Error: Missing pagination information in response: {pagination}")
                return None
            
            if pagination["page"] >= pagination["pages"]:
                break

            page_number += 1
        
        except requests.exceptions.HTTPError as err:
            print(err)
            return None    
        except Exception as err:
            print(err)
            return None
        
    return all_samples

samples = fetch_samples(dataPortalURL)

print("Sample metadata acquired.")
print("Associating samples with projects...")

def clean_up(projects, samples):

    keys_to_remove_project = ["active", "accepted", "uuid", "current_status", "started_date", "closed_date" ]
    keys_to_rename_project = {"award_doi": "doi"}

    keys_to_remove_member = ["id", "url"]
    keys_to_rename_member = {"project_role": "role", "institution": "org"} 
    
    keys_to_remove_sample = ["study_id", "elevation", "sample_type", "geolocation"]
    keys_to_rename_sample = {"proposal_id": "dataset_id", "collection_date": "date_added"} 

    for project in projects:

        for key in keys_to_remove_project:
            project.pop(key, None)
        for old_key, new_key in keys_to_rename_project.items():
            if old_key in project:
                project[new_key] = project.pop(old_key)

        if "project_members" in project and isinstance(project["project_members"], list):
            for member in project["project_members"]:

                for key in keys_to_remove_member:
                    member.pop(key, None)
                for old_key, new_key in keys_to_rename_member.items():
                    if old_key in member:
                        member[new_key] = member.pop(old_key)

                if "first_name" in member and "last_name" in member:
                    member["name"] = f"{member['first_name']} {member['last_name']}"
                    member.pop("first_name")
                    member.pop("last_name")
        
        if "uri" in project:
            project["uri"] = "https://sc-data.emsl.pnnl.gov/?projectId=" + project["id"]
                
    for sample in samples:

        for key in keys_to_remove_sample:
            sample.pop(key, None)
        for old_key, new_key in keys_to_rename_sample.items():
            if old_key in sample:
                sample[new_key] = sample.pop(old_key)
    
        metadata_keys = [k for k in sample.keys() if re.match(r".*_metadata", k)] # metadata key is dynamically named
        for metadata_key in metadata_keys:
            sample.pop(metadata_key, None)

        # Example: EMSL:12345_1
        sample["id"] = "EMSL:" + sample["dataset_id"] + "_" + sample["sampling_set"]
        sample.pop("sampling_set", 0)

    return projects, samples

cleaned_projects, cleaned_samples = clean_up(projects, samples)

print("Data cleanup complete.")
print("Writing data to files...")

#write these ro emsl_data with indent 4
with open("emsl_data.json", "w") as file:
    json.dump({"projects": cleaned_projects, "samples": cleaned_samples}, file, indent=4)

print("Data written to emsl_data.json.")
print("Done.")
