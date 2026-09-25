<?xml version="1.0" encoding="UTF-8"?>
<!-- Side-by-side review of the artwork conversion, one figure per landscape page:
     the original PNG, the SVG generated from it, and the pixel difference.

     Figures are numbered and ordered as the specification numbers them - document
     order of <figure> in UBL.xml - so a reviewer can say "figure 12" and everyone
     is looking at the same diagram. File names are shown too, but small.

       saxon -s:UBL.xml -xsl:imageTriptych.xsl -o:triptych.fo \
             art-dir=... svg-dir=... diff-dir=... include="Base1 Base2 ..."
       fop triptych.fo triptych.pdf

     Only figures named in `include` are emitted, keeping their true figure
     numbers, so the deck holds the conversions under review and nothing else.

     red  = ink the original has and the SVG lost
     blue = ink the SVG invented                                              -->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:fo="http://www.w3.org/1999/XSL/Format"
  xmlns:xs="http://www.w3.org/2001/XMLSchema"
  xmlns:u="urn:ubl-triptych"
  exclude-result-prefixes="xs u"
  version="3.0">

<xsl:output method="xml" indent="no"/>

<xsl:param name="art-dir"  as="xs:string"/>
<xsl:param name="svg-dir"  as="xs:string"/>
<xsl:param name="diff-dir" as="xs:string"/>
<!-- The third panel shows only what the SVG *lost*, with the absent elements
     numbered: on a busy diagram the two colours and their boxes overlap until
     neither can be read, and a missing element is the half that matters first -
     an invented line is a line in the wrong place, a missing one can be a whole
     start event that is not there. Pass diff-suffix=-marked.png for both colours,
     or -diff-r2.png for the raw pixel difference. -->
<xsl:param name="diff-suffix" as="xs:string" select="'-marked-lost.png'"/>
<xsl:param name="diff-caption" as="xs:string" select="'Lost from the SVG'"/>
<!-- The middle panel shows the classification copy of the SVG: same drawing,
     coloured by what each element was classified as, so a reviewer checks the
     reading and the fidelity on one page. The difference panel is computed from
     the plain black SVG whatever is shown here - colour cannot affect it. Pass
     svg-suffix=.svg to show the plain drawing instead. -->
<xsl:param name="svg-suffix"  as="xs:string" select="'-classified.svg'"/>
<xsl:param name="svg-caption" as="xs:string"
           select="'Generated SVG, coloured by classification'"/>
<!-- space-separated basenames to include; empty means every figure -->
<xsl:param name="include" as="xs:string" select="''"/>
<!-- optional: directory of -struct.json reports, to print each figure's verdict -->
<xsl:param name="verdict-dir" as="xs:string" select="''"/>
<!-- A3 landscape by default: three diagrams across A4 landscape is too small to
     judge anything by -->
<xsl:param name="page-width"  as="xs:string" select="'420mm'"/>
<xsl:param name="page-height" as="xs:string" select="'297mm'"/>

<xsl:variable name="wanted" as="xs:string*" select="tokenize(normalize-space($include), '\s+')"/>

<xsl:function name="u:base" as="xs:string">
  <xsl:param name="ref" as="xs:string"/>
  <xsl:sequence select="replace(replace($ref, '^.*/', ''), '\.[^.]*$', '')"/>
</xsl:function>

<xsl:function name="u:uri" as="xs:string">
  <xsl:param name="dir" as="xs:string"/>
  <xsl:param name="file" as="xs:string"/>
  <xsl:sequence select="'file://' || replace($dir, '/$', '') || '/' || $file"/>
</xsl:function>

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
            <fo:inline color="#2a78d6">action</fo:inline> ·
            <fo:inline color="#e34948">document</fo:inline> ·
            <fo:inline color="#1baf7a">start</fo:inline> ·
            <fo:inline color="#eda100">end</fo:inline> ·
            <fo:inline color="#4a3aa7">decision/note</fo:inline> ·
            <fo:inline color="#008300">fork bar</fo:inline> ·
            <fo:inline color="#8a8a85">structure</fo:inline>
            <fo:inline color="#999"> | third panel: </fo:inline>
            <xsl:choose>
              <!-- the legend has to say what this deck's third panel actually
                   shows, or the page contradicts its own picture -->
              <xsl:when test="$diff-suffix = '-marked-lost.png'">
                <fo:inline color="#D40000">red</fo:inline>
                <xsl:text> = line-work the original has and the SVG does not, text
                  excluded; what the SVG invented is in the list, not the picture</xsl:text>
              </xsl:when>
              <xsl:otherwise>
                <fo:inline color="#D40000">red</fo:inline>
                <xsl:text> = ink the original has and the SVG does not, </xsl:text>
                <fo:inline color="#0060D0">blue</fo:inline>
                <xsl:text> = ink the SVG invented. Every pixel, text included, at
                  the 2px radius - not the line-work measure the verdict uses</xsl:text>
              </xsl:otherwise>
            </xsl:choose></fo:inline>
          <fo:leader leader-pattern="space"/>
          <fo:inline>page <fo:page-number/></fo:inline>
        </fo:block>
      </fo:static-content>

      <fo:flow flow-name="xsl-region-body">
        <xsl:apply-templates select="//figure[imageobject/imagedata/@fileref
                                            or .//imagedata/@fileref]"/>
      </fo:flow>
    </fo:page-sequence>
  </fo:root>
</xsl:template>

<xsl:template match="figure">
  <!-- The figure's label, as the published specification writes it: figures in
       the body run 1, 2, 3... and a figure inside an appendix takes that
       appendix's letter and its own position within it. UBL-1.0-Procurement-
       Process sits in Appendix C, the revision history, and the specification
       calls it "Figure C.1" - counting straight through the document called it
       91, which is a figure number the document does not have. Checked against
       the published UBL 2.5: the other 77 diagrams here agree either way, and
       that one did not. -->
  <xsl:variable name="app" select="ancestor::appendix[1]"/>
  <xsl:variable name="n" as="xs:string" select="
      if ($app) then
        codepoints-to-string(64 + count($app/preceding-sibling::appendix) + 1)
        || '.'
        || string(count($app//figure[.//imagedata/@fileref]
                        intersect preceding::figure) + 1)
      else
        string(count(preceding::figure[.//imagedata/@fileref]
                     [not(ancestor::appendix)]) + 1)"/>
  <xsl:variable name="ref" as="xs:string" select="string((.//imagedata/@fileref)[1])"/>
  <xsl:variable name="base" as="xs:string" select="u:base($ref)"/>
  <xsl:if test="empty($wanted) or $base = $wanted">
    <xsl:variable name="first" as="xs:boolean"
                  select="not(preceding::figure[.//imagedata/@fileref]
                              [empty($wanted) or u:base(string((.//imagedata/@fileref)[1])) = $wanted])"/>
    <fo:block break-before="{if ($first) then 'auto' else 'page'}">

      <fo:block space-after="3mm">
        <fo:block font-size="15pt" font-weight="bold">
          <xsl:value-of select="'Figure ' || $n"/>
          <xsl:if test="normalize-space(title)">
            <xsl:value-of select="' - ' || normalize-space(title)"/>
          </xsl:if>
        </fo:block>
        <fo:block font-size="8pt" color="#777" space-before="1mm">
          <xsl:value-of select="$base"/>
          <xsl:if test="$verdict-dir != ''">
            <!-- the verdict, when a report for this figure is to hand; a missing or
                 unreadable one simply leaves the line off -->
            <xsl:try>
              <xsl:variable name="v"
                  select="json-doc(u:uri($verdict-dir, $base || '-struct.json'))"/>
              <xsl:text>  -  </xsl:text>
              <fo:inline font-weight="bold"
                  color="{if ($v?verdict = 'correct') then '#177245'
                          else if ($v?verdict = 'needs-human') then '#8a6d00'
                          else '#a02020'}">
                <xsl:value-of select="upper-case(string($v?verdict))"/>
              </fo:inline>
              <xsl:if test="$v?verdict != 'correct'">
                <xsl:value-of select="'  (' ||
                  string-join((
                    if ($v?structural?absent      gt 0) then $v?structural?absent      || ' absent'  else (),
                    if ($v?structural?invented    gt 0) then $v?structural?invented    || ' invented' else (),
                    if ($v?structural?textAbsent  gt 0) then $v?structural?textAbsent  || ' text absent' else (),
                    if ($v?structural?textDiffers gt 0) then $v?structural?textDiffers || ' text differs' else (),
                    if ($v?structural?coherence   gt 0) then $v?structural?coherence   || ' incoherent' else (),
                    if (count($v?human?*) gt 0) then count($v?human?*) || ' to check' else ()
                  ), ', ') || ')'"/>
              </xsl:if>
              <xsl:catch/>
            </xsl:try>
          </xsl:if>
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
              <xsl:with-param name="caption" select="'Original (art/' || $base || '.png)'"/>
              <xsl:with-param name="src" select="u:uri($art-dir, $base || '.png')"/>
            </xsl:call-template>
            <fo:table-cell><fo:block/></fo:table-cell>
            <xsl:call-template name="panel">
              <xsl:with-param name="caption" select="$svg-caption"/>
              <xsl:with-param name="src" select="u:uri($svg-dir, $base || $svg-suffix)"/>
            </xsl:call-template>
            <fo:table-cell><fo:block/></fo:table-cell>
            <xsl:call-template name="panel">
              <xsl:with-param name="caption" select="$diff-caption"/>
              <xsl:with-param name="src" select="u:uri($diff-dir, $base || $diff-suffix)"/>
            </xsl:call-template>
          </fo:table-row>
        </fo:table-body>
      </fo:table>

      <!-- what those numbers are. The list is not written here: it comes from the
           report, in the order the numbers were drawn in, so the caption and the
           picture cannot drift apart. -->
      <xsl:if test="$verdict-dir != ''">
        <xsl:try>
          <xsl:variable name="v"
              select="json-doc(u:uri($verdict-dir, $base || '-struct.json'))"/>
          <xsl:if test="exists($v?review?*)">
            <fo:block space-before="3mm" font-size="7.5pt">
              <xsl:for-each select="$v?review?*">
                <xsl:sort select="?n" data-type="number"/>
                <xsl:if test="position() le 14">
                  <fo:block space-after="0.6mm">
                    <fo:inline font-weight="bold"
                        color="{if (?what = 'absent') then '#D00000'
                                else if (?what = 'invented') then '#0060D0'
                                else if (?what = 'check') then '#967000'
                                else '#D67A00'}">
                      <xsl:value-of select="?n || '. ' || ?what"/>
                    </fo:inline>
                    <xsl:if test="?where != ''">
                      <fo:inline color="#777">
                        <xsl:value-of select="'  [' || ?where || ']'"/>
                      </fo:inline>
                    </xsl:if>
                    <xsl:if test="?detail != ''">
                      <xsl:value-of select="'  ' || ?detail"/>
                    </xsl:if>
                    <xsl:if test="?check != ''">
                      <fo:inline font-style="italic" color="#555">
                        <xsl:value-of select="'  -  ' || ?check"/>
                      </fo:inline>
                    </xsl:if>
                  </fo:block>
                </xsl:if>
              </xsl:for-each>
              <xsl:if test="count($v?review?*) gt 14">
                <fo:block color="#777">
                  <xsl:value-of select="'... and ' || (count($v?review?*) - 14) ||
                                        ' more, all numbered on the difference image'"/>
                </fo:block>
              </xsl:if>
            </fo:block>
          </xsl:if>
          <xsl:catch/>
        </xsl:try>
      </xsl:if>
    </fo:block>
  </xsl:if>
</xsl:template>

<xsl:template name="panel">
  <xsl:param name="caption" as="xs:string"/>
  <xsl:param name="src" as="xs:string"/>
  <fo:table-cell border="0.3pt solid #ccc" padding="2mm">
    <fo:block font-size="8.5pt" font-weight="bold" color="#444" space-after="2mm">
      <xsl:value-of select="$caption"/>
    </fo:block>
    <!-- width alone: the artwork is at most 1.42 times as tall as it is wide, so
         122mm across is at most 173mm down and always fits the body. Constraining
         the height as well would fix the viewport at that height and leave most of
         every page empty. -->
    <fo:block text-align="center">
      <fo:external-graphic src="url('{$src}')"
        content-width="122mm" scaling="uniform"/>
    </fo:block>
  </fo:table-cell>
</xsl:template>

</xsl:stylesheet>
