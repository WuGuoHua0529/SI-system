import json
import os
import uuid

RULES_FILE = 'rules.json'

class RulesStore:
    def __init__(self):
        self.rules = []
        self.load_rules()

    def load_rules(self):
        if not os.path.exists(RULES_FILE):
            self.rules = []
            return
        
        try:
            with open(RULES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.rules = data if isinstance(data, list) else []
                
                # Migration: Add source and tags if missing
                migrated = False
                for r in self.rules:
                    if 'source' not in r:
                        r['source'] = 'IEC'
                        migrated = True
                    if 'tags' not in r or not isinstance(r.get('tags'), list):
                        r['tags'] = []
                        migrated = True
                
                if migrated:
                    self.save_rules()
        except Exception as e:
            print(f"Error loading rules: {e}")
            self.rules = []

    def save_rules(self):
        try:
            with open(RULES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.rules, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving rules: {e}")

    def add_rule(self, name, query, source, tags=None):
        rule = {
            "id": str(uuid.uuid4()),
            "name": name,
            "query": query,
            "source": source,
            "tags": tags if tags is not None else [],
            "lastChecked": None,
            "latestDocumentName": None,
            "previousDocumentName": None,
            "hasNewUpdate": False
        }
        self.rules.append(rule)
        self.save_rules()
        return rule

    def remove_rule(self, rule_id):
        self.rules = [r for r in self.rules if r['id'] != rule_id]
        self.save_rules()

    def update_rule(self, updated_rule):
        for i, r in enumerate(self.rules):
            if r['id'] == updated_rule['id']:
                self.rules[i] = updated_rule
                break
        self.save_rules()

    def get_rules_by_source(self, source):
        return [r for r in self.rules if r.get('source', 'IEC') == source]

    def get_rules_by_tag(self, tag):
        return [r for r in self.rules if tag in r.get('tags', [])]

    def add_tag_to_rule(self, rule_id, tag):
        for r in self.rules:
            if r['id'] == rule_id:
                tags = r.setdefault('tags', [])
                if tag not in tags:
                    tags.append(tag)
                    self.save_rules()
                break

    def remove_tag_from_rule(self, rule_id, tag):
        for r in self.rules:
            if r['id'] == rule_id:
                tags = r.get('tags', [])
                if tag in tags:
                    tags.remove(tag)
                    self.save_rules()
                break

    def remove_tag_from_all_rules(self, tag):
        changed = False
        for r in self.rules:
            tags = r.get('tags', [])
            if tag in tags:
                tags.remove(tag)
                changed = True
        if changed:
            self.save_rules()
