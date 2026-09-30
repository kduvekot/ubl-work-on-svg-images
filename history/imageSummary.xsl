<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:xs="http://www.w3.org/2001/XMLSchema"
  xmlns:math="http://www.w3.org/2005/xpath-functions/math"
  xmlns:file="http://expath.org/ns/file"
  exclude-result-prefixes="xs math file"
  version="3.0">

<xsl:param name="new-dir" as="xs:string" required="yes"/>
  
<xsl:template match="/">
<root xmlns="http://www.w3.org/1999/XSL/Format" 
      font-family="Times" font-size="10pt">

  <layout-master-set>
    <simple-page-master master-name="frame" 
                        page-height="297mm" page-width="210mm" 
                        margin-top="15mm" margin-bottom="15mm" 
                        margin-left="15mm" margin-right="15mm">
      <region-body region-name="frame-body"/>
    </simple-page-master>
  </layout-master-set>
  
  <page-sequence master-reference="frame">
    <flow flow-name="frame-body">
      <xsl:for-each select="//imagedata/@fileref">
        <xsl:variable name="new-name" select="
                $new-dir || replace(.,'^(.+/)?(.+?)\.[^.]+$','$2') || '.svg'"/>
        <block space-before="1em" keep-with-next="always">
          <xsl:value-of select="position() || '. ' || ancestor::figure/title"/>
        </block>
        <table border="solid 1pt">
          <table-column column-width="50%"/>
          <table-column column-width="50%"/>
          <table-body>
            <table-row>
              <table-cell border="solid 1pt" display-align="after">
                <block>
                  <external-graphic content-width="scale-to-fit"
                                    width="100%" src="{
                                      replace(base-uri(/),'/[^/]+$','/')}{.}"/>
                </block>
              </table-cell>
              <table-cell border="solid 1pt" display-align="after">
                <block>
                  <xsl:choose>
                    <xsl:when test="file:exists($new-name)">
                      <external-graphic content-width="scale-to-fit"
                                        width="100%"
                                        src="{$new-name}"/>
                    </xsl:when>
                    <xsl:otherwise>
                      <inline color="red">File not found</inline>
                      <xsl:message select="'Missing:',$new-name"/>
                    </xsl:otherwise>
                  </xsl:choose>
                </block>
              </table-cell>
            </table-row>
            <table-row keep-with-previous="always">
              <table-cell border="solid 1pt" display-align="after">
                <block text-align="center">
                  <xsl:value-of select="."/>
                </block>
              </table-cell>
              <table-cell border="solid 1pt" display-align="after">
                <block text-align="center">
                  <xsl:value-of select="$new-name"/>
                </block>
              </table-cell>
            </table-row>
          </table-body>
        </table>
      </xsl:for-each>
    </flow>
  </page-sequence>
  <xsl:variable name="old-list" 
                      select="file:list(replace(base-uri(/),'/[^/]+$','/art'))! 
                              replace(.,'\.[^.]+$','')"/>
  <xsl:variable name="new-list" 
                select="file:list($new-dir)[not(starts-with(.,'.'))] ! 
                              replace(.,'^(.+/)?(.+?)\.[^.]+$','$2') "/>
  <xsl:for-each select="$new-list[not(.=$old-list)]">
    <xsl:message select="'Extra:',."/>
  </xsl:for-each>
</root>
</xsl:template>

</xsl:stylesheet>