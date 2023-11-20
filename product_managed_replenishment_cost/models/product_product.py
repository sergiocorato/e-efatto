# Copyright 2021 Sergio Corato <https://github.com/sergiocorato>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# flake8: noqa: C901

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    standard_price = fields.Float(string="Landed with adjustment/depreciation")
    adjustment_cost = fields.Float(
        string="Adjustment Cost (€/pz)",
        digits="Product Price",
        compute="_compute_adjustment_cost",
        inverse="_inverse_adjustment_cost",
        search="_search_adjustment_cost",
        groups="base.group_user",
    )
    landed_cost = fields.Float(
        string="Landed cost",
        digits="Product Price",
        compute="_compute_landed_cost",
        inverse="_inverse_landed_cost",
        search="_search_landed_cost",
        groups="base.group_user",
        help="The cost that you have to support in order to produce or "
        "acquire the goods without adjustment/depreciation.",
    )

    @api.depends("product_variant_ids", "product_variant_ids.adjustment_cost")
    def _compute_adjustment_cost(self):
        unique_variants = self.filtered(lambda tmpl: len(tmpl.product_variant_ids) == 1)
        for template in unique_variants:
            template.adjustment_cost = template.product_variant_ids.adjustment_cost
        for template in self - unique_variants:
            template.adjustment_cost = 0.0

    def _inverse_adjustment_cost(self):
        if len(self.product_variant_ids) == 1:
            self.product_variant_ids.adjustment_cost = self.adjustment_cost

    def _search_adjustment_cost(self, operator, value):
        products = self.env["product.product"].search(
            [("adjustment_cost", operator, value)], limit=None
        )
        return [("id", "in", products.mapped("product_tmpl_id").ids)]

    @api.depends("product_variant_ids", "product_variant_ids.landed_cost")
    def _compute_landed_cost(self):
        unique_variants = self.filtered(
            lambda templ: len(templ.product_variant_ids) == 1
        )
        for template in unique_variants:
            template.landed_cost = template.product_variant_ids.landed_cost
        for template in self - unique_variants:
            template.landed_cost = 0.0

    def _inverse_landed_cost(self):
        self.ensure_one()
        if len(self.product_variant_ids) == 1:
            self.product_variant_ids.landed_cost = self.landed_cost

    def _search_landed_cost(self, operator, value):
        products = self.env["product.product"].search(
            [("landed_cost", operator, value)]
        )
        return [("id", "in", products.mapped("product_tmpl_id").ids)]


class ProductProduct(models.Model):
    _inherit = "product.product"

    standard_price = fields.Float(string="Landed with adjustment/depreciation")
    adjustment_cost = fields.Float(
        string="Adjustment Cost (€/pz)",
        company_dependent=True,
        groups="base.group_user",
        digits="Product Price",
    )
    landed_cost = fields.Float(
        string="Landed cost",
        company_dependent=True,
        groups="base.group_user",
        digits="Product Price",
        help="The cost that you have to support in order to produce or "
        "acquire the goods without adjustment/depreciation.",
    )

    def _get_managed_price_from_bom(self, boms_to_recompute=False):
        self.ensure_one()
        bom = self.env["mrp.bom"]._bom_find(product=self)
        return self._compute_bom_managed_price(bom, boms_to_recompute=boms_to_recompute)

    def _compute_bom_managed_price(self, bom, boms_to_recompute=False):
        self.ensure_one()
        update_standard_price = self.env.context.get("update_standard_price", False)
        if not bom:
            return 0
        if not boms_to_recompute:
            boms_to_recompute = []
        total = 0
        total_landed = 0
        for opt in bom.operation_ids:
            duration_expected = (
                opt.workcenter_id.time_start
                + opt.workcenter_id.time_stop
                + opt.time_cycle
            )
            duration_cost = (duration_expected / 60) * opt.workcenter_id.costs_hour
            total += duration_cost
            total_landed += duration_cost
        for line in bom.bom_line_ids:
            if line._skip_bom_line(self):
                continue

            # Compute recursive if line has `child_line_ids`
            if line.child_bom_id and line.child_bom_id in boms_to_recompute:
                (
                    child_total,
                    child_total_landed,
                ) = line.product_id._compute_bom_managed_price(
                    line.child_bom_id, boms_to_recompute=boms_to_recompute
                )
                total += (
                    line.product_id.uom_id._compute_price(
                        child_total, line.product_uom_id
                    )
                    * line.product_qty
                )
                total_landed += (
                    line.product_id.uom_id._compute_price(
                        child_total_landed, line.product_uom_id
                    )
                    * line.product_qty
                )
            else:
                cost = (
                    line.product_id.standard_price
                    if update_standard_price
                    else line.product_id.managed_replenishment_cost
                )
                # landed cost is updated in the same time of standard price, so use
                # always this
                cost_landed = line.product_id.landed_cost
                total += (
                    line.product_id.uom_id._compute_price(cost, line.product_uom_id)
                    * line.product_qty
                )
                total_landed += (
                    line.product_id.uom_id._compute_price(
                        cost_landed, line.product_uom_id
                    )
                    * line.product_qty
                )
        product_price = bom.product_uom_id._compute_price(
            total / (bom.product_qty or 1), self.uom_id
        )
        landed_price = bom.product_uom_id._compute_price(
            total_landed / (bom.product_qty or 1), self.uom_id
        )
        return product_price, landed_price

    def _get_price_unit_from_seller(self, seller):
        price_unit = 0.0
        margin_percentage = 0.0
        if seller.price:
            price_unit = seller.price
            if hasattr(seller, "discount"):
                price_unit = price_unit * (1 - seller.discount / 100.0)
            if hasattr(seller, "discount2") and hasattr(seller, "discount3"):
                price_unit = price_unit * (1 - seller.discount2 / 100.0)
                price_unit = price_unit * (1 - seller.discount3 / 100.0)
            if seller.currency_id != self.env.company.currency_id:
                price_unit = seller.currency_id._convert(
                    seller.price,
                    self.env.company.currency_id,
                    self.env.company,
                    fields.Date.today(),
                    round=False,
                )
        if seller.product_uom != self.uom_id:
            price_unit = seller.product_uom._compute_price(price_unit, self.uom_id)
        # add tariff cost on country group
        margin_percentage += sum(
            seller.name.country_id.mapped(
                "country_group_ids.logistic_charge_percentage"
            )
        )
        if margin_percentage:
            price_unit *= 1 + margin_percentage / 100.0
        tariff_id = self.intrastat_code_id.tariff_id
        if tariff_id:
            price_unit *= 1 + tariff_id.tariff_percentage / 100.0
        return price_unit

    def update_products_tobe_purchased(self):
        products_without_seller_price = self.env["product.product"]
        for product in self:
            if product.seller_ids and product.seller_ids[0].price:
                seller = product.seller_ids[0]
                price_unit = product._get_price_unit_from_seller(seller)
                landed_cost = price_unit
                # add adjustment and depreciation costs
                adjustment_cost = product.adjustment_cost
                depreciation_cost = seller.depreciation_cost
                price_unit += adjustment_cost + depreciation_cost
                if self.env.context.get("update_managed_replenishment_cost", False):
                    product.managed_replenishment_cost = price_unit
                if self.env.context.get("update_standard_price", False):
                    product.standard_price = price_unit
                    product.landed_cost = landed_cost
            else:
                products_without_seller_price |= product
        return products_without_seller_price

    def _get_all_bom_raw_components(self, bom):
        all_raw_components = self.env["product.product"]
        all_manuf_components = self.env["product.product"]
        for line in bom.bom_line_ids:
            if line.child_bom_id:
                (
                    raw_components,
                    manuf_components,
                ) = line.product_id._get_all_bom_raw_components(line.child_bom_id)
                all_raw_components |= raw_components
                all_manuf_components |= manuf_components
                all_manuf_components |= line.product_id
            elif line.product_id:
                all_raw_components |= line.product_id
        return all_raw_components, all_manuf_components

    def update_managed_replenishment_cost(self):
        update_standard_price = self.env.context.get("update_standard_price", False)
        update_managed_replenishment_cost = self.env.context.get(
            "update_managed_replenishment_cost", False
        )
        update_bom_products_list_price_weight = self.env.context.get(
            "update_bom_products_list_price_weight", False
        )
        products_with_bom = (
            self.filtered(lambda product: product.bom_count)
            if update_bom_products_list_price_weight
            else self.env["product.product"]
        )
        # update cost for products to be purchased first, then them to be manufactured
        products_tobe_purchased = self.filtered(
            lambda x: x.seller_ids and not x.bom_count
        )
        products_nottobe_purchased = self.filtered(
            lambda x: not x.seller_ids and not x.bom_count
        )
        products_tobe_manufactured = self - (
            products_tobe_purchased + products_nottobe_purchased
        )
        all_raw_components = self.env["product.product"]
        for product in products_tobe_manufactured:
            # get all raw component prices to update before update product manufactured
            bom = self.env["mrp.bom"]._bom_find(product=product)
            raw_components, manuf_components = product._get_all_bom_raw_components(bom)
            all_raw_components |= raw_components
            products_tobe_manufactured |= manuf_components
        products_tobe_purchased |= all_raw_components.filtered(lambda x: x.seller_ids)
        products_nottobe_purchased |= all_raw_components.filtered(
            lambda x: not x.seller_ids
        )
        products_without_seller_price = (
            products_tobe_purchased.update_products_tobe_purchased()
        )
        # compute replenishment cost for product without suppliers
        for product in products_nottobe_purchased:
            if update_managed_replenishment_cost:
                product.managed_replenishment_cost = product.standard_price
            if update_standard_price:
                product.landed_cost = product.standard_price
            # these products are without seller nor bom
        # compute replenishment cost for product to be manufactured, with or without
        # suppliers
        for product in self.sort_products_by_parent(products_tobe_manufactured):
            produce_price, landed_price = product._get_managed_price_from_bom()
            produce_price += product.adjustment_cost
            if product.seller_ids:
                seller = product.seller_ids[0]
                produce_price += seller.depreciation_cost
            if update_managed_replenishment_cost:
                product.managed_replenishment_cost = produce_price
            if update_standard_price:
                product.standard_price = produce_price
                product.landed_cost = landed_price

        for product in products_with_bom:
            (
                product.list_price,
                product.weight,
            ) = product.get_bom_price_weight_from_first_child_components()

        return products_nottobe_purchased, products_without_seller_price

    def get_bom_price_weight_from_first_child_components(self):
        bom_id = self.bom_ids[0]
        component_list_price = self.uom_id._compute_quantity(
            sum(
                (x.product_id.list_price * x.product_qty for x in bom_id.bom_line_ids)
                or [0]
            )
            / (bom_id.product_qty or 1),
            bom_id.product_uom_id,
        )
        component_weight = self.uom_id._compute_quantity(
            sum(
                (
                    x.product_id.weight_uom_id._compute_quantity(
                        x.product_id.weight * x.product_qty, self.weight_uom_id
                    )
                    for x in bom_id.bom_line_ids
                )
                or [0]
            )
            / (bom_id.product_qty or 1),
            bom_id.product_uom_id,
        )
        return component_list_price, component_weight

    def sort_products_by_parent(self, products):
        product_ids = self.env["product.product"]
        for product in products:
            # this is used as component
            if product.bom_line_ids:
                product_ids |= product
        for product in products:
            # add other for last
            if product not in product_ids:
                product_ids |= product
        return product_ids
