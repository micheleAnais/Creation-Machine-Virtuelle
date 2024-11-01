import json
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl
import requests
from pyVmomi import vim, vmodl

# Ignorer les certificats non sécurisés (optionnel)
context = ssl._create_unverified_context()

# Charger les informations de configuration de l'OVA depuis le fichier JSON
with open("config.json") as config_file:
    config = json.load(config_file)

# Connexion à l'hôte ESXi
si = SmartConnect(host="192.168.127.128", user="root", pwd="toto32**", sslContext=context)

def import_ova(si, config):
    # Obtenez le data center, le datastore et le réseau
    datacenter = si.content.rootFolder.childEntity[0]
    datastore = None
    network = None

    for ds in datacenter.datastore:
        if ds.name == config["datastore_name"]:
            datastore = ds
            break
    
    for nw in datacenter.network:
        if nw.name == config["network_name"]:
            network = nw
            break

    # Vérifier si le datastore et le réseau existent
    if not datastore or not network:
        print("Datastore ou réseau introuvable.")
        return

    # Préparation de la spécification pour l'importation de l'OVA
    manager = si.content.ovfManager
    spec_params = vim.OvfManager.CreateImportSpecParams(entityName=config["vm_name"])

    # Lire le fichier OVA
    with open(config["ova_path"], "rb") as ova_file:
        ovf_descriptor = ova_file.read()

    # Créer une spécification d'importation
    import_spec = manager.CreateImportSpec(ovf_descriptor, resourcePool=datacenter.hostFolder.childEntity[0].resourcePool, datastore=datastore, cisp=spec_params)

    # Vérification des erreurs dans la spécification
    if import_spec.error:
        for e in import_spec.error:
            print(f"Erreur d'importation : {e.msg}")
        return

    # Démarrer la tâche d'importation
    lease = datacenter.hostFolder.childEntity[0].resourcePool.ImportVApp(import_spec.importSpec, vmFolder=datacenter.vmFolder)
    
    # Attendre la fin du déploiement
    while lease.state == vim.HttpNfcLease.State.initializing:
        pass
    
    if lease.state == vim.HttpNfcLease.State.ready:
        print("L'importation de l'OVA a commencé.")
        for device_url in lease.info.deviceUrl:
            url = device_url.url.replace("*", config["host_ip"])
            headers = {'Content-Type': 'application/x-vnd.vmware-streamVmdk'}
            with open(config["ova_path"], "rb") as f:
                requests.put(url, data=f, headers=headers, verify=False)
        lease.HttpNfcLeaseComplete()
        print("OVA importée avec succès.")
    else:
        print("Erreur durant l'importation de l'OVA.")
        lease.HttpNfcLeaseAbort()

# Exécution de la fonction pour importer l'OVA
import_ova(si, config)

# Déconnexion de l'ESXi
Disconnect(si)