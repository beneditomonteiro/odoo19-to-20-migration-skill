-- Odoo 20 crm_iap_mine rebuilt crm.iap.lead.industry (sic_group/division_id NOT NULL, new xmlids, unique name).
-- Odoo 19 rows keep old xmlids and collide on crm_iap_lead_industry_name_uniq. Pure reference data (IAP mining
-- request M2M only): drop stale rows so the module re-creates them. Run before installing/upgrading crm_iap_mine.
delete from crm_iap_lead_industry_crm_iap_lead_mining_request_rel;
delete from ir_model_data where module='crm_iap_mine' and model='crm.iap.lead.industry';
delete from crm_iap_lead_industry;
