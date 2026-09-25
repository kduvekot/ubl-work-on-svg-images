<?xml version="1.0" encoding="UTF-8"?>
<!-- A saved baseline against a new run, one figure per landscape page: the
     baseline's SVG and the new SVG, both rendered at the original PNG's own pixel
     width, and the pixel difference between them.

       saxon -s:UBL.xml -xsl:baselineCompare.xsl -o:compare.fo \
             compare-dir=... include="Base1 Base2 ..." baseline-label=2026-09-25
       fop compare.fo compare.pdf

     <compare-dir> is what tools/compare-to-baseline.sh wrote: per figure
     -base.png, -new.png, -basediff.png and -compare.json, and summary.json.

     red  = ink only the baseline has
     blue = ink only the new SVG has
     grey = ink both have, drawn faintly so a blank difference still shows which
            drawing it is

     Figures are numbered as the specification numbers them, exactly as in
     imageTriptych.xsl, so "figure 12" means the same page in both decks.      -->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:fo="http://www.w3.org/1999/XSL/Format"
  xmlns:xs="http://www.w3.org/2001/XMLSchema"
  xmlns:u="urn:ubl-baseline-compare"
  exclude-result-prefixes="xs u"
  version="3.0">

<xsl:output method="xml" indent="no"/>

<xsl:param name="compare-dir" as="xs:string"/>
<xsl:param name="include" as="xs:string" select="''"/>
<xsl:param name="baseline-label" as="xs:string" select="'baseline'"/>
<xsl:param name="new-label" as="xs:string" select="'new run'"/>
<xsl:param name="page-width"  as="xs:string" select="'420mm'"/>
<xsl:param name="page-height" as="xs:string" select="'297mm'"/>

<xsl:variable name="wanted" as="xs:string*" select="tokenize(normalize-space($include), '\s+')"/>

<xsl:function name="u:base" as="xs:string">
  <xsl:param name="ref" as="xs:string"/>
  <xsl:sequence select="replace(replace($ref, '^.*/', ''), '\.[^.]*$', '')"/>
</xsl:function>

<xsl:function name="u:uri" as="xs:string">
  <xsl:param name="file" as="xs:string"/>
  <xsl:sequence select="'file://' || replace($compare-dir, '/$', '') || '/' || $file"/>
</xsl:function>

<!-- a figure's label as the specification writes it: 1, 2, 3... in the body, and
     the appendix letter and position inside an appendix (see imageTriptych.xsl) -->
<xsl:function name="u:number" as="xs:string">
  <xsl:param name="f" as="element(figure)"/>
  <xsl:variable name="app" select="$f/ancestor::appendix[1]"/>
  <xsl:sequence select="
      if ($app) then
        codepoints-to-string(64 + count($app/preceding-sibling::appendix) + 1)
        || '.'
        || string(count($app//figure[.//imagedata/@fileref]
                        intersect $f/preceding::figure) + 1)
      else
        string(count($f/preceding::figure[.//imagedata/@fileref]
                     [not(ancestor::appendix)]) + 1)"/>
</xsl:function>

<xsl:variable name="figures" as="element(figure)*"
    select="//figure[.//imagedata/@fileref]
                    [empty($wanted) or u:base(string((.//imagedata/@fileref)[1])) = $wanted]"/>

<xsl:template match="/">
  <fo:root font-family="Helvetica, Arial, sans-serif">
    <fo:layout-master-set>
      <fo:simple-page-master master-name="land"
          page-width="{$page-width}" page-height="{$page-height}"
          margin-top="8mm" margin-bottom="8mm" margin-left="10mm" margin-right="10mm">
        <fo:region-body margin-top="17mm" margin-bottom="9mm"/>
        <fo:region-before extent="16mm"/>
        <fo:region-after  extent="8mm"/>
      </fo:simple-page-master>
    </fo:layout-master-set>

    <fo:page-sequence master-reference="land">
      <fo:static-content flow-name="xsl-region-after">
        <fo:block font-size="8pt" color="#666" border-top="0.3pt solid #ccc"
                  padding-top="1.5mm" text-align-last="justify">
          <fo:inline>
            <xsl:text>third panel: </xsl:text>
            <fo:inline color="#D40000">red</fo:inline>
            <xsl:text> = ink only the baseline SVG has, </xsl:text>
            <fo:inline color="#0060D0">blue</fo:inline>
            <xsl:text> = ink only the new SVG has, grey = ink both have. Every pixel, text
              included, at radius 0 and with no alignment: nothing is forgiven.</xsl:text>
          </fo:inline>
          <fo:leader leader-pattern="space"/>
          <fo:inline>page <fo:page-number/></fo:inline>
        </fo:block>
      </fo:static-content>

      <fo:flow flow-name="xsl-region-body">
        <xsl:call-template name="summary"/>
        <xsl:apply-templates select="$figures"/>
      </fo:flow>
    </fo:page-sequence>
  </fo:root>
</xsl:template>

<!-- the whole set on one page first: how many are identical, and which are not -->
<xsl:template name="summary">
  <xsl:variable name="s" select="json-doc(u:uri('summary.json'))"/>
  <fo:block font-size="15pt" font-weight="bold" space-after="2mm">
    <xsl:value-of select="'Baseline ' || $baseline-label || ' against ' || $new-label"/>
  </fo:block>
  <fo:block font-size="10pt" space-after="5mm">
    <fo:inline font-weight="bold" color="{if ($s?differs = 0 and $s?notCompared = 0)
                                          then '#177245' else '#a02020'}">
      <xsl:value-of select="$s?identical || ' of ' || count($s?figures?*) || ' identical'"/>
    </fo:inline>
    <xsl:value-of select="'  -  ' || $s?differs || ' differ, ' || $s?notCompared
                          || ' could not be compared. Identical means every pixel of the two
                          renders is the same.'"/>
  </fo:block>
  <fo:table table-layout="fixed" width="100%" font-size="8pt">
    <fo:table-column column-width="14mm"/>
    <fo:table-column column-width="proportional-column-width(1)"/>
    <fo:table-column column-width="22mm"/>
    <fo:table-column column-width="24mm"/>
    <fo:table-column column-width="22mm"/>
    <fo:table-column column-width="22mm"/>
    <fo:table-column column-width="18mm"/>
    <fo:table-column column-width="18mm"/>
    <fo:table-column column-width="18mm"/>
    <fo:table-header font-weight="bold" color="#444">
      <fo:table-row border-bottom="0.3pt solid #999">
        <xsl:for-each select="('Figure', 'Diagram', 'Result', 'Pixels differ',
                               'Baseline only', 'New only', 'SVG', 'draw.io', 'Spec')">
          <fo:table-cell padding="0.8mm"><fo:block><xsl:value-of select="."/></fo:block></fo:table-cell>
        </xsl:for-each>
      </fo:table-row>
    </fo:table-header>
    <fo:table-body>
      <xsl:for-each select="$figures">
        <xsl:variable name="base" select="u:base(string((.//imagedata/@fileref)[1]))"/>
        <xsl:variable name="c" select="$s?figures?*[?name = $base]"/>
        <fo:table-row>
          <fo:table-cell padding="0.5mm"><fo:block><xsl:value-of select="u:number(.)"/></fo:block></fo:table-cell>
          <fo:table-cell padding="0.5mm"><fo:block><xsl:value-of select="$base"/></fo:block></fo:table-cell>
          <fo:table-cell padding="0.5mm">
            <fo:block font-weight="bold"
                color="{if ($c?verdict = 'identical') then '#177245' else '#a02020'}">
              <xsl:value-of select="upper-case(string(($c?verdict, 'not compared')[1]))"/>
            </fo:block>
          </fo:table-cell>
          <xsl:for-each select="('pixelsDiffer', 'onlyInBaseline', 'onlyInNew')">
            <xsl:variable name="k" select="."/>
            <fo:table-cell padding="0.5mm"><fo:block><xsl:value-of select="$c($k)"/></fo:block></fo:table-cell>
          </xsl:for-each>
          <xsl:for-each select="('svgIdentical', 'drawioIdentical', 'specIdentical')">
            <xsl:variable name="k" select="."/>
            <fo:table-cell padding="0.5mm">
              <fo:block color="{if ($c($k) = false()) then '#a02020' else '#444'}">
                <xsl:value-of select="if (empty($c($k))) then '-'
                                      else if ($c($k)) then 'same bytes' else 'differs'"/>
              </fo:block>
            </fo:table-cell>
          </xsl:for-each>
        </fo:table-row>
      </xsl:for-each>
    </fo:table-body>
  </fo:table>
</xsl:template>

<xsl:template match="figure">
  <xsl:variable name="base" as="xs:string" select="u:base(string((.//imagedata/@fileref)[1]))"/>
  <fo:block break-before="page">
    <fo:block space-after="3mm">
      <fo:block font-size="15pt" font-weight="bold">
        <xsl:value-of select="'Figure ' || u:number(.)"/>
        <xsl:if test="normalize-space(title)">
          <xsl:value-of select="' - ' || normalize-space(title)"/>
        </xsl:if>
      </fo:block>
      <fo:block font-size="8pt" color="#777" space-before="1mm">
        <xsl:value-of select="$base"/>
        <xsl:try>
          <xsl:variable name="c" select="json-doc(u:uri($base || '-compare.json'))"/>
          <xsl:text>  -  </xsl:text>
          <fo:inline font-weight="bold"
              color="{if ($c?verdict = 'identical') then '#177245' else '#a02020'}">
            <xsl:value-of select="upper-case(string($c?verdict))"/>
          </fo:inline>
          <xsl:value-of select="'  (' || $c?pixelsDiffer || ' pixels differ: '
                                || $c?onlyInBaseline || ' ink only in the baseline, '
                                || $c?onlyInNew || ' only in the new SVG; SVG '
                                || (if ($c?svgIdentical) then 'byte-identical' else 'bytes differ')
                                || ')'"/>
          <xsl:catch>
            <xsl:text>  -  NOT COMPARED</xsl:text>
          </xsl:catch>
        </xsl:try>
      </fo:block>
    </fo:block>

    <fo:table table-layout="fixed" width="100%">
      <fo:table-column column-width="proportional-column-width(1)"/>
      <fo:table-column column-width="4mm"/>
      <fo:table-column column-width="proportional-column-width(1)"/>
      <fo:table-column column-width="4mm"/>
      <fo:table-column column-width="proportional-column-width(1)"/>
      <fo:table-body>
        <fo:table-row>
          <xsl:call-template name="panel">
            <xsl:with-param name="caption" select="'Baseline SVG (' || $baseline-label || ')'"/>
            <xsl:with-param name="src" select="u:uri($base || '-base.png')"/>
          </xsl:call-template>
          <fo:table-cell><fo:block/></fo:table-cell>
          <xsl:call-template name="panel">
            <xsl:with-param name="caption" select="'New SVG (' || $new-label || ')'"/>
            <xsl:with-param name="src" select="u:uri($base || '-new.png')"/>
          </xsl:call-template>
          <fo:table-cell><fo:block/></fo:table-cell>
          <xsl:call-template name="panel">
            <xsl:with-param name="caption"
                select="'Difference: red only in the baseline, blue only in the new SVG'"/>
            <xsl:with-param name="src" select="u:uri($base || '-basediff.png')"/>
          </xsl:call-template>
        </fo:table-row>
      </fo:table-body>
    </fo:table>
  </fo:block>
</xsl:template>

<xsl:template name="panel">
  <xsl:param name="caption" as="xs:string"/>
  <xsl:param name="src" as="xs:string"/>
  <fo:table-cell border="0.3pt solid #ccc" padding="2mm">
    <fo:block font-size="8.5pt" font-weight="bold" color="#444" space-after="2mm">
      <xsl:value-of select="$caption"/>
    </fo:block>
    <fo:block text-align="center">
      <fo:external-graphic src="url('{$src}')" content-width="122mm" scaling="uniform"/>
    </fo:block>
  </fo:table-cell>
</xsl:template>

</xsl:stylesheet>
