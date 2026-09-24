"""Liens d'affiliation avec sous-identifiant par vidéo (étape 27).

Une seule fonction fabrique l'URL suivie (`lien_pour`) : la description, le commentaire épinglé
et le manifeste emploient donc **le même** sous-identifiant, condition pour que l'import des
conversions (`import_revenue.py`) retrouve la vidéo.

- Le sous-identifiant ne porte que `video_id`, `channel_id` et la langue : aucune donnée
  personnelle (`Product.sub_id_format`, jetons fermés).
- Les mentions ne se retirent jamais : la ligne du réseau vient de `config/languages/<lang>.yaml`
  (contractuelle) ; la surcharge du produit **s'ajoute** à elle, elle ne la remplace pas.
"""

from __future__ import annotations

from pathlib import Path

from factory.core.models import SUBID_EN_CHEMIN, LienAffiliation


def lien_pour(produit, channel_id: str, lang: str, video_id: str) -> LienAffiliation:
    """Lien suivi d'un produit pour une vidéo. Sans attribution par vidéo, l'URL sort telle quelle."""
    subid = produit.subid(channel_id, lang, video_id)
    url = produit.target_url
    if subid and produit.subid_param:
        if produit.network in SUBID_EN_CHEMIN:
            url = f"{url.rstrip('/')}/{subid}"
        else:
            url = f"{url}{'&' if '?' in url else '?'}{produit.subid_param}={subid}"
    return LienAffiliation(
        network=produit.network, tracking_id=produit.tracking_id,
        subid_param=produit.subid_param, subid_value=subid, target_url=url,
        product_id=produit.id,
    )


def mentions(produit, langue, lang: str) -> list[str]:
    """Mention du réseau (langue), puis celle du produit si elle diffère. Jamais moins."""
    lignes = [langue.disclosure.pour_reseau(produit.network)]
    surcharge = produit.disclosure_override.get(lang)
    if surcharge is not None and surcharge.description_line not in lignes:
        lignes.append(surcharge.description_line)
    return lignes


def ligne_de_tete(produits, langue) -> str:
    """« PAID PROMOTION — #ad » : générique de la langue puis mention de chaque réseau."""
    reseaux: list[str] = []
    for produit in produits:
        ligne = langue.disclosure.pour_reseau(produit.network)
        if ligne not in reseaux:
            reseaux.append(ligne)
    return " — ".join([langue.disclosure.overlay_generic.upper(), *reseaux])


def lignes_produit(produit, lien: LienAffiliation, langue, lang: str,
                   deja: str = "") -> list[str]:
    """Lignes d'un produit ; une mention déjà portée par la ligne de tête `deja` n'est pas redite."""
    cta = produit.cta_text.get(lang, "").strip()
    tete = f"{cta} {produit.name}" if cta else produit.name
    suite = [m for m in mentions(produit, langue, lang) if m not in deja.split(" — ")]
    return [f"{tete} : {lien.target_url}", *suite]


def build_links(video_id: str, racine: Path | None = None, product_id: str | None = None,
                ecrire: bool = True) -> list[LienAffiliation]:
    """Liens d'un run, écrits dans `manifest.conformite.affiliate_links`.

    `product_id` force un produit (sinon celui de la spec, puis ceux de la chaîne). Un run
    sans produit rend une liste vide et n'écrit rien.
    """
    from factory.core import config as config_module
    from factory.core import runs
    from factory.core.paths import RunPaths, racine_projet
    from factory.editorial.seo import produits_de

    racine = racine or racine_projet()
    chemins = RunPaths.depuis_video_id(video_id, racine)
    spec = runs.charger_spec(video_id, racine)
    cfg = config_module.charger(racine, strict=False)
    channel = cfg.get_channel(spec.channel_id)
    if product_id:
        if product_id not in cfg.products:
            raise KeyError(f"produit inconnu : {product_id} (config/products/)")
        produits = [cfg.products[product_id]]
    else:
        produits = produits_de(channel, cfg, spec)
    liens = [lien_pour(p, channel.id, channel.lang, spec.video_id) for p in produits]
    if liens and ecrire:
        manifest = runs.charger_manifest(video_id, racine)
        manifest.conformite.affiliate_links = liens
        manifest.conformite.paid_promotion = True
        runs.ecrire_json(chemins.manifest, manifest)
    return liens
