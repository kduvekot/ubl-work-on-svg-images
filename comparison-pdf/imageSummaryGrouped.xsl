<?xml version="1.0" encoding="UTF-8"?>
<!-- Grouped variant of imageSummary.xsl: the same PNG/SVG comparison, but the
     figures are collected into coherent groups so a reviewer compares like with
     like, and each entry is labelled with how far its conversion has actually got.

     Invocation is unchanged:
       xslt2pe UBL.xml utilities/images/imageSummaryGrouped.xsl compare.fo new-dir=.../
-->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:xs="http://www.w3.org/2001/XMLSchema"
  xmlns:file="http://expath.org/ns/file"
  xmlns:svg="http://www.w3.org/2000/svg"
  xmlns:u="urn:x-ubl:image-summary"
  exclude-result-prefixes="xs file svg u"
  version="3.0">

<xsl:param name="new-dir" as="xs:string" required="yes"/>

<!-- ==== group catalogue ================================================== -->
<!-- Order here is the order of the report. "kind" is the coarse split the TC
     asked for: process diagrams vs pictorial illustrations vs reference figures. -->
<xsl:variable name="groups" as="element(g)*">
  <g id="G1"  kind="Process diagrams — UML activity" label="Procurement — Catalogue"
     check="Catalogue provision flows: lane titles, document names, decision labels."/>
  <g id="G2"  kind="Process diagrams — UML activity" label="Procurement — Pre-award and Tendering"
     check="The largest family. Check lane order and that every tender document keeps its exact name."/>
  <g id="G3"  kind="Process diagrams — UML activity" label="Procurement — Ordering and Quotation"
     check="Post-award ordering; overview diagrams are dense, check nothing is dropped."/>
  <g id="G4"  kind="Process diagrams — UML activity" label="Procurement — Vendor Managed Inventory (VMI, CRP, ROCD)"
     check="Three near-identical families; confirm each variant kept its own distinguishing steps."/>
  <g id="G5"  kind="Process diagrams — UML activity" label="Plan — Collaborative Planning, Forecasting and Replenishment"
     check="CPFR process flows; check exception-handling branches survived."/>
  <g id="G6"  kind="Process diagrams — UML activity" label="Pay — Billing and Payment"
     check="Billing variants differ only in the note type used; check Credit vs Debit vs Self-billed."/>
  <g id="G7"  kind="Process diagrams — UML activity" label="Deliver — Logistics and Transport"
     check="Despatch/receipt advice and intermodal freight; check transport party lane titles."/>
  <g id="G8"  kind="Process diagrams — UML activity" label="Deliver — Cross-Border Regulatory Reporting"
     check="Customs and Goods Item Passport flows. These five use Inkscape flowRoot text — see the legend."/>
  <g id="G9"  kind="Process diagrams — UML activity" label="Business Directory and Agreements"
     check="Business card, digital capability and agreement processes."/>
  <g id="G10" kind="Process diagrams — UML activity" label="Historical (Revision History)"
     check="Retained for the revision history; conversion fidelity matters less than legibility."/>
  <g id="G11" kind="Process diagrams — BPMN 2.0" label="BPMN collaboration diagrams"
     check="Pools and lanes, thin-ring start events, heavy-ring end events, X-marked exclusive gateways, dotted message flows with envelope markers. Check the event ring weights and the gateway markers survived — they carry the semantics."/>
  <g id="G12" kind="Process diagrams — other notations" label="CPFR step models (VICS notation)"
     check="Block-arrow data flows, folded-corner document icons, actor figures, shaded step bands. Not UML, not BPMN. Check the block arrows keep their direction and the step-band labels."/>
  <g id="G13" kind="Process diagrams — other notations" label="Chevron and phase overviews"
     check="High-level phase maps drawn as chevrons. Few elements, so any loss is obvious; check chevron overlap and actor figures."/>
  <g id="G14" kind="Reference figures" label="Structural and conceptual figures"
     check="Not process flows — dependency charts, data-model and Open-edi figures. These are the least converted."/>
  <g id="G15" kind="Pictorial illustrations" label="Shipment vs. Consignment scenes"
     check="Not flow diagrams — drawn scenes with clip-art. Embedded bitmap clip-art here may be acceptable; check the LABELS are live text."/>
</xsl:variable>

<!-- ==== classification ================================================== -->
<xsl:function name="u:group" as="xs:string">
  <xsl:param name="base"  as="xs:string"/>
  <xsl:param name="chain" as="xs:string"/>
  <xsl:sequence select="
    (: notation determined by inspecting the original PNG artwork, not the filename :)
    if ($base = ('UBL-2.3-OrderingProcess','UBL-2.4-BusinessInformation'))
      then 'G11'                                     (: BPMN 2.0 :)
    else if ($base = ('UBL-2.2-CPFR-Steps1-2','UBL-2.2-CPFR-Steps3-4-5',
                      'UBL-2.2-CPFR-Steps6-9'))
      then 'G12'                                     (: VICS CPFR step model :)
    else if ($base = ('UBL-2.2-IMFM-GenericIntermodalFreightProcess',
                      'UBL-2.3-Pre-awardProcess','UBL-2.3-ProcurementProcess'))
      then 'G13'                                     (: chevron / phase overview :)
    else if ($base = ('UBL-2.2-SchemaDependencies','UBL-2.2-UDT-QDT','UBL-2.3-ModelRealization',
                      'UBL-2.2-Open-edi-Overview','UBL-2.2-Open-edi-Application',
                      'UBL-2.2-DefaultValidation'))
      then 'G14'                                     (: structural / conceptual :)
    else if ($base = ('UBL-2.2-Fulfilment-1simple','UBL-2.2-Fulfilment-2split',
                      'UBL-2.2-Fulfilment-3intermediary','UBL-2.2-Fulfilment-4consolidated'))
      then 'G15'                                     (: pictorial :)
    else if (contains($chain,'Revision History'))            then 'G10'
    else if (contains($chain,'Business Directory'))          then 'G9'
    else if (contains($chain,'Cross-Border'))                then 'G8'
    else if (contains($chain,'Vendor Managed Inventory'))    then 'G4'
    else if (contains($chain,'Collaborative Planning'))      then 'G5'
    else if (contains($chain,'Catalogue'))                   then 'G1'
    else if (contains($chain,'Pre-award'))                   then 'G2'
    else if (contains($chain,'Ordering') or contains($chain,'Quotation')) then 'G3'
    else if (contains($chain,'&gt; Pay &gt;'))               then 'G6'
    else if (contains($chain,'&gt; Deliver &gt;'))           then 'G7'
    else 'G14'"/>
</xsl:function>

<!-- How far has this file actually been converted? Read the SVG and look. -->
<xsl:function name="u:state" as="xs:string">
  <xsl:param name="uri" as="xs:string"/>
  <xsl:choose>
    <xsl:when test="not(doc-available($uri))">unreadable</xsl:when>
    <xsl:otherwise>
      <xsl:variable name="d" select="doc($uri)"/>
      <xsl:variable name="rasters" select="count($d//svg:image)"/>
      <xsl:variable name="texts"   select="count($d//svg:text)"/>
      <xsl:sequence select="if ($rasters = 0)   then 'vector'
                       else if ($texts &lt; 5)  then 'bitmap'
                       else 'hybrid'"/>
    </xsl:otherwise>
  </xsl:choose>
</xsl:function>

<xsl:function name="u:colour" as="xs:string">
  <xsl:param name="state" as="xs:string"/>
  <xsl:sequence select="if ($state='vector') then '#106b21'
                   else if ($state='hybrid') then '#8a6100'
                   else '#a11'"/>
</xsl:function>

<!-- ==== the entries ===================================================== -->
<xsl:variable name="entries" as="element(e)*">
  <xsl:for-each select="//imagedata/@fileref">
    <xsl:variable name="base" select="replace(.,'^(.+/)?(.+?)\.[^.]+$','$2')"/>
    <xsl:variable name="new"  select="$new-dir || $base || '.svg'"/>
    <xsl:variable name="chain"
      select="string-join(ancestor::*[title]/normalize-space(title),' &gt; ')"/>
    <e pos="{position()}" base="{$base}" new="{$new}"
       old="{replace(base-uri(/),'/[^/]+$','/')}{.}" oldref="{.}"
       title="{normalize-space(ancestor::figure/title)}"
       group="{u:group($base,$chain)}"
       exists="{file:exists($new)}"
       state="{if (file:exists($new)) then u:state($new) else 'missing'}"/>
  </xsl:for-each>
</xsl:variable>

<xsl:template match="/">
<root xmlns="http://www.w3.org/1999/XSL/Format"
      font-family="Times" font-size="10pt">

  <layout-master-set>
    <simple-page-master master-name="frame"
                        page-height="297mm" page-width="210mm"
                        margin-top="15mm" margin-bottom="15mm"
                        margin-left="15mm" margin-right="15mm">
      <region-body region-name="frame-body" margin-bottom="8mm"/>
      <region-after region-name="frame-foot" extent="6mm"/>
    </simple-page-master>
  </layout-master-set>

  <bookmark-tree>
    <xsl:for-each-group select="$groups" group-by="@kind">
      <bookmark internal-destination="kind-{position()}">
        <bookmark-title><xsl:value-of select="current-grouping-key()"/></bookmark-title>
        <xsl:for-each select="current-group()">
          <xsl:if test="$entries[@group = current()/@id]">
            <bookmark internal-destination="{@id}">
              <bookmark-title><xsl:value-of select="@label"/></bookmark-title>
            </bookmark>
          </xsl:if>
        </xsl:for-each>
      </bookmark>
    </xsl:for-each-group>
  </bookmark-tree>

  <page-sequence master-reference="frame">
    <static-content flow-name="frame-foot">
      <block font-size="8pt" text-align="end" color="#666">
        <page-number/>
      </block>
    </static-content>
    <flow flow-name="frame-body">

      <!-- front matter -->
      <block font-size="16pt" font-weight="bold" space-after="4pt">
        UBL artwork: original PNG compared to draft SVG
      </block>
      <block font-size="9pt" color="#444" space-after="10pt">
        Grouped by kind of image, then by area of the specification.
        <xsl:value-of select="' ' || count($entries) || ' figures. Generated ' ||
                              format-date(current-date(),'[D1] [MNn] [Y0001]') || '.'"/>
      </block>

      <block font-weight="bold" space-after="3pt">How far each conversion has got</block>
      <list-block provisional-distance-between-starts="22mm" space-after="8pt"
                  font-size="9pt">
        <xsl:for-each select="('vector','hybrid','bitmap')">
          <list-item>
            <list-item-label end-indent="label-end()">
              <block font-weight="bold" color="{u:colour(.)}">
                <xsl:value-of select="."/>
              </block>
            </list-item-label>
            <list-item-body start-indent="body-start()">
              <block>
                <xsl:value-of select="
                  if (.='vector') then 'true vector artwork — no bitmap inside the SVG'
                  else if (.='hybrid') then 'vector drawing with bitmap clip-art embedded'
                  else 'a bitmap wrapped in an SVG element — not yet converted'"/>
              </block>
            </list-item-body>
          </list-item>
        </xsl:for-each>
      </list-block>

      <block font-weight="bold" space-after="3pt">Groups</block>
      <table font-size="9pt" space-after="10pt" border="solid 0.5pt #999">
        <table-column column-width="42%"/>
        <table-column column-width="20%"/>
        <table-column column-width="9.5%"/>
        <table-column column-width="9.5%"/>
        <table-column column-width="9.5%"/>
        <table-column column-width="9.5%"/>
        <table-header>
          <table-row font-weight="bold" background-color="#eee">
            <xsl:for-each select="('Group','Kind','Figs','vector','hybrid','bitmap')">
              <table-cell border="solid 0.5pt #999" padding="2pt">
                <block><xsl:value-of select="."/></block>
              </table-cell>
            </xsl:for-each>
          </table-row>
        </table-header>
        <table-body>
          <xsl:for-each select="$groups">
            <xsl:variable name="in" select="$entries[@group = current()/@id]"/>
            <xsl:if test="$in">
              <table-row>
                <table-cell border="solid 0.5pt #999" padding="2pt">
                  <block><xsl:value-of select="@label"/></block>
                </table-cell>
                <table-cell border="solid 0.5pt #999" padding="2pt">
                  <block><xsl:value-of select="@kind"/></block>
                </table-cell>
                <xsl:for-each select="(string(count($in)),
                                       string(count($in[@state='vector'])),
                                       string(count($in[@state='hybrid'])),
                                       string(count($in[@state='bitmap'])))">
                  <table-cell border="solid 0.5pt #999" padding="2pt">
                    <block text-align="center"><xsl:value-of select="."/></block>
                  </table-cell>
                </xsl:for-each>
              </table-row>
            </xsl:if>
          </xsl:for-each>
          <table-row font-weight="bold" background-color="#f4f4f4">
            <table-cell border="solid 0.5pt #999" padding="2pt" number-columns-spanned="2">
              <block>Total</block>
            </table-cell>
            <xsl:for-each select="(string(count($entries)),
                                   string(count($entries[@state='vector'])),
                                   string(count($entries[@state='hybrid'])),
                                   string(count($entries[@state='bitmap'])))">
              <table-cell border="solid 0.5pt #999" padding="2pt">
                <block text-align="center"><xsl:value-of select="."/></block>
              </table-cell>
            </xsl:for-each>
          </table-row>
        </table-body>
      </table>

      <block font-size="9pt" color="#444" space-after="2pt">
        "Fig n" is the figure's number in the ungrouped comparison, so feedback
        can be cross-referenced between the two documents.
      </block>

      <!-- the groups -->
      <xsl:for-each-group select="$groups" group-by="@kind">
        <xsl:variable name="kpos" select="position()"/>
        <xsl:if test="$entries[@group = current-group()/@id]">
          <block id="kind-{$kpos}" break-before="page"
                 font-size="14pt" font-weight="bold" space-after="6pt"
                 border-bottom="solid 1pt #333" padding-bottom="2pt">
            <xsl:value-of select="current-grouping-key()"/>
            <xsl:value-of select="' (' ||
              count($entries[@group = current-group()/@id]) || ' figures)'"/>
          </block>

          <xsl:for-each select="current-group()">
            <xsl:variable name="in" select="$entries[@group = current()/@id]"/>
            <xsl:if test="$in">
              <block id="{@id}" font-size="11pt" font-weight="bold"
                     space-before="10pt" space-after="1pt" keep-with-next="always">
                <xsl:value-of select="@label || ' — ' || count($in) || ' figures'"/>
              </block>
              <block font-size="9pt" color="#444" space-after="4pt"
                     keep-with-next="always">
                <xsl:value-of select="@check"/>
              </block>

              <xsl:for-each select="$in">
                <block space-before="1em" keep-with-next="always">
                  <inline color="#666" font-size="9pt">
                    <xsl:value-of select="'Fig ' || @pos || '. '"/>
                  </inline>
                  <xsl:value-of select="@title"/>
                  <inline font-size="9pt" font-weight="bold"
                          color="{u:colour(@state)}">
                    <xsl:value-of select="'  [' || @state || ']'"/>
                  </inline>
                </block>
                <table border="solid 1pt">
                  <table-column column-width="50%"/>
                  <table-column column-width="50%"/>
                  <table-body>
                    <table-row>
                      <table-cell border="solid 1pt" display-align="after">
                        <block>
                          <external-graphic content-width="scale-to-fit"
                                            width="100%" src="{@old}"/>
                        </block>
                      </table-cell>
                      <table-cell border="solid 1pt" display-align="after">
                        <block>
                          <xsl:choose>
                            <xsl:when test="@exists='true'">
                              <external-graphic content-width="scale-to-fit"
                                                width="100%" src="{@new}"/>
                            </xsl:when>
                            <xsl:otherwise>
                              <inline color="red">File not found</inline>
                              <xsl:message select="'Missing:',string(@new)"/>
                            </xsl:otherwise>
                          </xsl:choose>
                        </block>
                      </table-cell>
                    </table-row>
                    <table-row keep-with-previous="always">
                      <table-cell border="solid 1pt" display-align="after">
                        <block text-align="center" font-size="9pt">
                          <xsl:value-of select="@oldref"/>
                        </block>
                      </table-cell>
                      <table-cell border="solid 1pt" display-align="after">
                        <block text-align="center" font-size="9pt">
                          <xsl:value-of select="@new"/>
                        </block>
                      </table-cell>
                    </table-row>
                  </table-body>
                </table>
              </xsl:for-each>
            </xsl:if>
          </xsl:for-each>
        </xsl:if>
      </xsl:for-each-group>

    </flow>
  </page-sequence>

  <!-- unreferenced files, as in the original stylesheet -->
  <xsl:variable name="old-list"
                select="file:list(replace(base-uri(/),'/[^/]+$','/art'))!
                        replace(.,'\.[^.]+$','')"/>
  <xsl:variable name="new-list"
                select="file:list($new-dir)[not(starts-with(.,'.'))] !
                        replace(.,'^(.+/)?(.+?)\.[^.]+$','$2')"/>
  <xsl:for-each select="$new-list[not(.=$old-list)]">
    <xsl:message select="'Extra:',."/>
  </xsl:for-each>
  <xsl:for-each select="$old-list[not(.=$entries/@base)]">
    <xsl:message select="'Unreferenced by UBL.xml:',."/>
  </xsl:for-each>
</root>
</xsl:template>

</xsl:stylesheet>
